from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_payment_status = fields.Selection(
        [
            ("unpaid", "Belum Lunas"),
            ("partial", "Sebagian"),
            ("paid", "Lunas"),
        ],
        string="Payment Settlement Status",
        compute="_compute_invoice_payment_status",
        store=True,
    )
    invoice_payment_log_ids = fields.One2many(
        "invoice.payment.log",
        "invoice_id",
        string="Payment History",
        readonly=True,
    )
    invoice_payment_log_count = fields.Integer(
        string="Payment Log Count",
        compute="_compute_invoice_payment_log_count",
    )

    @api.depends("payment_state", "amount_residual", "state")
    def _compute_invoice_payment_status(self):
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund") or move.state != "posted":
                move.invoice_payment_status = False
            elif move.payment_state == "paid" or move.amount_residual == 0:
                move.invoice_payment_status = "paid"
            elif move.payment_state in ("partial", "in_payment") or (
                0 < move.amount_residual < move.amount_total
            ):
                move.invoice_payment_status = "partial"
            else:
                move.invoice_payment_status = "unpaid"

    def _compute_invoice_payment_log_count(self):
        log_data = self.env["invoice.payment.log"].read_group(
            [("invoice_id", "in", self.ids)],
            ["invoice_id"],
            ["invoice_id"],
        )
        mapped_data = {
            data["invoice_id"][0]: data["invoice_id_count"] for data in log_data
        }
        for move in self:
            move.invoice_payment_log_count = mapped_data.get(move.id, 0)

    def action_open_register_invoice_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Register Invoice Payment",
            "res_model": "register.invoice.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_ref": self.name,
                "default_invoice_id": self.id,
                "default_amount": self.amount_residual,
            },
        }

    def action_view_invoice_payment_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Payment History",
            "res_model": "invoice.payment.log",
            "view_mode": "tree,form",
            "domain": [("invoice_id", "=", self.id)],
            "context": {"default_invoice_id": self.id},
        }

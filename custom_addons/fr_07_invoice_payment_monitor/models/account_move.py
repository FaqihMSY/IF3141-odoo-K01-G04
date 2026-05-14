from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    fr07_payment_status = fields.Selection(
        [
            ("unpaid", "Belum Lunas"),
            ("partial", "Sebagian"),
            ("paid", "Lunas"),
        ],
        string="FR-07 Payment Status",
        compute="_compute_fr07_payment_status",
        store=True,
    )
    fr07_payment_log_ids = fields.One2many(
        "fr07.invoice.payment.log",
        "invoice_id",
        string="FR-07 Payment History",
        readonly=True,
    )
    fr07_payment_log_count = fields.Integer(
        string="FR-07 Payment Log Count",
        compute="_compute_fr07_payment_log_count",
    )

    @api.depends("payment_state", "amount_residual", "state")
    def _compute_fr07_payment_status(self):
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund") or move.state != "posted":
                move.fr07_payment_status = False
            elif move.payment_state == "paid" or move.amount_residual == 0:
                move.fr07_payment_status = "paid"
            elif move.payment_state in ("partial", "in_payment") or (
                0 < move.amount_residual < move.amount_total
            ):
                move.fr07_payment_status = "partial"
            else:
                move.fr07_payment_status = "unpaid"

    def _compute_fr07_payment_log_count(self):
        log_data = self.env["fr07.invoice.payment.log"].read_group(
            [("invoice_id", "in", self.ids)],
            ["invoice_id"],
            ["invoice_id"],
        )
        mapped_data = {
            data["invoice_id"][0]: data["invoice_id_count"] for data in log_data
        }
        for move in self:
            move.fr07_payment_log_count = mapped_data.get(move.id, 0)

    def action_fr07_open_register_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "FR-07 Register Invoice Payment",
            "res_model": "fr07.register.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_ref": self.name,
                "default_invoice_id": self.id,
                "default_amount": self.amount_residual,
            },
        }

    def action_fr07_view_payment_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "FR-07 Payment History",
            "res_model": "fr07.invoice.payment.log",
            "view_mode": "tree,form",
            "domain": [("invoice_id", "=", self.id)],
            "context": {"default_invoice_id": self.id},
        }

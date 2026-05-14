from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RegisterInvoicePaymentWizard(models.TransientModel):
    _name = "register.invoice.payment.wizard"
    _description = "Register Invoice Payment"

    invoice_ref = fields.Char(string="Invoice Number", required=True)
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        domain=[("move_type", "=", "out_invoice"), ("state", "=", "posted")],
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="invoice_id.partner_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="invoice_id.currency_id",
        readonly=True,
    )
    amount = fields.Monetary(string="Paid Amount", required=True)
    payment_date = fields.Date(
        string="Payment Date",
        required=True,
        default=fields.Date.context_today,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Payment Method",
        required=True,
        domain=[("type", "in", ("bank", "cash"))],
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method Line",
        required=True,
    )
    note = fields.Char(string="Note")

    @api.onchange("invoice_ref")
    def _onchange_invoice_ref(self):
        if not self.invoice_ref:
            self.invoice_id = False
            return

        invoice = self._find_invoice(self.invoice_ref)
        self.invoice_id = invoice
        if invoice and not self.amount:
            self.amount = invoice.amount_residual

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        self.payment_method_line_id = False
        domain = [("journal_id", "=", self.journal_id.id), ("payment_type", "=", "inbound")]
        if self.journal_id:
            method_line = self.journal_id.inbound_payment_method_line_ids[:1]
            self.payment_method_line_id = method_line
        return {"domain": {"payment_method_line_id": domain}}

    @api.model
    def _find_invoice(self, invoice_ref):
        invoice = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("name", "=", invoice_ref.strip()),
            ],
            limit=1,
        )
        return invoice

    def _validate_payment(self, invoice):
        self.ensure_one()
        if not invoice:
            raise UserError(_("Invoice number was not found or invoice is not posted."))
        if invoice.payment_state == "paid" or invoice.amount_residual == 0:
            raise UserError(_("This invoice is already fully paid."))
        if self.amount <= 0:
            raise ValidationError(_("Paid amount must be greater than zero."))
        if self.amount > invoice.amount_residual:
            raise ValidationError(
                _(
                    "Paid amount cannot be greater than the invoice residual amount "
                    "(%s)."
                )
                % invoice.amount_residual
            )
        if self.payment_method_line_id.journal_id != self.journal_id:
            raise ValidationError(
                _("Payment method line must belong to the selected payment method.")
            )
        if self.payment_method_line_id.payment_type != "inbound":
            raise ValidationError(_("Payment method line must be an inbound method."))

    def action_confirm_payment(self):
        self.ensure_one()
        invoice = self.invoice_id or self._find_invoice(self.invoice_ref)
        self._validate_payment(invoice)

        register = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoice.ids,
        ).create(
            {
                "amount": self.amount,
                "payment_date": self.payment_date,
                "journal_id": self.journal_id.id,
                "payment_method_line_id": self.payment_method_line_id.id,
                "communication": self.note or invoice.name,
            }
        )
        payments = register._create_payments()

        invoice.invalidate_recordset()
        invoice._compute_invoice_payment_status()

        self.env["invoice.payment.log"].create(
            {
                "invoice_id": invoice.id,
                "amount": self.amount,
                "payment_date": self.payment_date,
                "journal_id": self.journal_id.id,
                "payment_method_line_id": self.payment_method_line_id.id,
                "payment_id": payments[:1].id,
                "status_after_payment": invoice.invoice_payment_status,
                "note": self.note,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Invoice"),
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }

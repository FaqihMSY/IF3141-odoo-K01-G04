from odoo import fields, models


class Fr07InvoicePaymentLog(models.Model):
    _name = "fr07.invoice.payment.log"
    _description = "FR-07 Invoice Payment History"
    _order = "payment_date desc, id desc"

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
        domain=[("move_type", "=", "out_invoice")],
    )
    invoice_number = fields.Char(
        string="Invoice Number",
        related="invoice_id.name",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="invoice_id.partner_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="invoice_id.currency_id",
        readonly=True,
    )
    amount = fields.Monetary(string="Paid Amount", required=True)
    payment_date = fields.Date(string="Payment Date", required=True)
    journal_id = fields.Many2one("account.journal", string="Payment Method", required=True)
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Payment Method Line",
        readonly=True,
    )
    payment_id = fields.Many2one("account.payment", string="Odoo Payment", readonly=True)
    status_after_payment = fields.Selection(
        [
            ("unpaid", "Belum Lunas"),
            ("partial", "Sebagian"),
            ("paid", "Lunas"),
        ],
        string="Status After Payment",
        readonly=True,
    )
    note = fields.Char(string="Note")

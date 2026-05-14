from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_invoice_generated = fields.Boolean(
        string="Automatically Generated Invoice",
        copy=False,
        readonly=True,
        help="Technical marker for invoices generated automatically from completed sales deliveries.",
    )

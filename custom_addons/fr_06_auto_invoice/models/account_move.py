from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    fr06_auto_generated = fields.Boolean(
        string="FR-06 Auto Generated",
        copy=False,
        readonly=True,
        help="Technical marker for invoices generated automatically by FR-06.",
    )

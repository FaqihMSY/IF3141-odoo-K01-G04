from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    on_time_rate = fields.Float(
        string="On Time Rate",
        readonly=True,
        help="Persentase ketepatan waktu pengiriman supplier.",
    )
    supplied_product_ids = fields.Many2many(
        "product.template",
        "res_partner_supplied_product_rel",
        "partner_id",
        "product_tmpl_id",
        string="Bahan Disuplai",
        domain=[("is_raw_material", "=", True)],
    )
    purchase_history_ids = fields.One2many(
        "purchase.order",
        "partner_id",
        string="Riwayat PO",
        readonly=True,
    )

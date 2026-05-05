from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_raw_material = fields.Boolean(
        string="Bahan Baku",
        help="Tandai produk ini sebagai bahan baku yang dikelola melalui Inventory Odoo.",
    )
    raw_material_notes = fields.Text(string="Catatan Bahan Baku")
    raw_material_reorder_point = fields.Float(
        string="Reorder Point",
        digits="Product Unit of Measure",
        help="Batas minimum stok bahan baku sebelum sistem menampilkan notifikasi kritis.",
    )
    raw_material_initial_quantity = fields.Float(
        string="Stok Awal",
        digits="Product Unit of Measure",
        help="Jumlah stok pembuka. Nilai ini hanya diproses saat bahan baku baru dibuat.",
    )
    is_stock_critical = fields.Boolean(
        string="Stok Kritis",
        compute="_compute_is_stock_critical",
        search="_search_is_stock_critical",
    )
    raw_material_stock_status = fields.Selection(
        [
            ("safe", "Aman"),
            ("critical", "Kritis"),
        ],
        string="Status Stok",
        compute="_compute_raw_material_stock_status",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_raw_material"):
                vals.setdefault("detailed_type", "product")

        products = super().create(vals_list)
        stock_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)

        for product, vals in zip(products, vals_list):
            initial_quantity = vals.get("raw_material_initial_quantity", 0.0)
            if not product.is_raw_material or not initial_quantity:
                continue
            if initial_quantity < 0:
                raise ValidationError(_("Stok awal bahan baku tidak boleh bernilai negatif."))
            if not stock_location:
                continue

            self.env["stock.quant"]._update_available_quantity(
                product.product_variant_id,
                stock_location,
                initial_quantity,
            )

        return products

    @api.constrains("raw_material_initial_quantity")
    def _check_raw_material_initial_quantity(self):
        for product in self:
            if product.raw_material_initial_quantity < 0:
                raise ValidationError(_("Stok awal bahan baku tidak boleh bernilai negatif."))

    @api.depends("is_raw_material", "qty_available", "raw_material_reorder_point")
    def _compute_is_stock_critical(self):
        for product in self:
            product.is_stock_critical = (
                product.is_raw_material
                and product.raw_material_reorder_point > 0
                and product.qty_available <= product.raw_material_reorder_point
            )

    def _search_is_stock_critical(self, operator, value):
        if operator not in ("=", "!="):
            return [("id", "=", 0)]

        critical_products = self.search([
            ("is_raw_material", "=", True),
            ("raw_material_reorder_point", ">", 0),
        ]).filtered(lambda product: product.qty_available <= product.raw_material_reorder_point)

        should_match_critical = (operator == "=" and value) or (operator == "!=" and not value)
        domain_operator = "in" if should_match_critical else "not in"
        return [("id", domain_operator, critical_products.ids)]

    @api.depends("is_raw_material", "qty_available", "raw_material_reorder_point")
    def _compute_raw_material_stock_status(self):
        for product in self:
            product.raw_material_stock_status = "critical" if product.is_stock_critical else "safe"

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    expected_delivery_date = fields.Date(
        string="Estimasi Pengiriman",
        required=True,
    )
    po_number = fields.Char(
        string="Nomor PO",
        related="name",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "unique_po_number",
            "unique(name, company_id)",
            "Nomor PO harus unik.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) in ("/", _("New")):
                vals["name"] = sequence.next_by_code("procurement.purchase.order") or _("New")

            expected_date = vals.get("expected_delivery_date")
            if expected_date and vals.get("order_line"):
                vals["order_line"] = self._apply_expected_date_to_lines(
                    vals["order_line"],
                    expected_date,
                )
        return super().create(vals_list)

    def write(self, vals):
        previous_dates = {order.id: order.expected_delivery_date for order in self}
        result = super().write(vals)
        if "expected_delivery_date" in vals:
            for order in self:
                order._sync_expected_date_to_lines(previous_dates.get(order.id))
        return result

    @api.onchange("expected_delivery_date")
    def _onchange_expected_delivery_date(self):
        for order in self:
            order._sync_expected_date_to_lines(order._origin.expected_delivery_date)

    def _sync_expected_date_to_lines(self, previous_date=None):
        for line in self.order_line:
            if not line.date_planned or (
                previous_date and line.date_planned == previous_date
            ):
                line.date_planned = self.expected_delivery_date

    @staticmethod
    def _apply_expected_date_to_lines(order_line_commands, expected_date):
        updated_commands = []
        for command in order_line_commands:
            if command[0] == 0 and isinstance(command[2], dict):
                command[2].setdefault("date_planned", expected_date)
            updated_commands.append(command)
        return updated_commands

    @api.constrains("partner_id", "expected_delivery_date")
    def _check_procurement_header(self):
        for order in self:
            if not order.partner_id or order.partner_id.supplier_rank <= 0:
                raise ValidationError(_("Supplier wajib dipilih."))
            if not order.expected_delivery_date:
                raise ValidationError(_("Estimasi tanggal pengiriman wajib diisi."))


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    manual_price_unit = fields.Float(
        string="Manual Unit Price",
        store=True,
        copy=False,
    )
    price_unit = fields.Float(
        string="Unit Price",
        digits="Product Price",
        readonly=False,
    )

    @api.onchange("price_unit")
    def _onchange_price_unit_manual(self):
        for line in self:
            if line.price_unit:
                line.manual_price_unit = line.price_unit

    @api.onchange("product_id")
    def onchange_product_id(self):
        if not self.product_id or (
            self.env.context.get("origin_po_id") and self.product_qty
        ):
            return

        manual_price = self.manual_price_unit or self.price_unit
        self.price_unit = self.product_qty = 0.0
        self._product_id_change()
        self._suggest_quantity()

        if manual_price:
            self.manual_price_unit = manual_price
            self.price_unit = manual_price

    @api.onchange("product_id", "product_qty", "product_uom")
    def _onchange_preserve_manual_price(self):
        for line in self:
            if line.manual_price_unit:
                line.price_unit = line.manual_price_unit

    @api.depends("product_qty", "product_uom", "company_id", "manual_price_unit")
    def _compute_price_unit_and_date_planned_and_name(self):
        super()._compute_price_unit_and_date_planned_and_name()
        for line in self:
            if line.manual_price_unit and not line.display_type:
                line.price_unit = line.manual_price_unit

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("price_unit"):
                vals.setdefault("manual_price_unit", vals["price_unit"])
        return super().create(vals_list)

    def write(self, values):
        if values.get("price_unit"):
            values = dict(values, manual_price_unit=values["price_unit"])
        return super().write(values)

    @api.constrains("product_id", "product_qty", "price_unit")
    def _check_procurement_line(self):
        for line in self:
            if line.product_qty <= 0:
                raise ValidationError(_("Jumlah bahan baku harus lebih dari 0."))
            if line.price_unit <= 0:
                raise ValidationError(_("Harga bahan baku harus lebih dari 0."))
            if line.product_id and not line.product_id.product_tmpl_id.is_raw_material:
                raise ValidationError(
                    _("Produk %s belum ditandai sebagai bahan baku.")
                    % line.product_id.display_name
                )

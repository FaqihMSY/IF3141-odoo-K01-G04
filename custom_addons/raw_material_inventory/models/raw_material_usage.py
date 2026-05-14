from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class RawMaterialUsage(models.Model):
    _name = "raw.material.usage"
    _description = "Raw Material Usage"
    _order = "date desc, id desc"

    name = fields.Char(
        string="Nomor Dokumen",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    date = fields.Datetime(
        string="Tanggal Pemakaian",
        required=True,
        default=fields.Datetime.now,
    )
    spk_reference = fields.Char(string="Referensi SPK", required=True)
    line_ids = fields.One2many(
        "raw.material.usage.line",
        "usage_id",
        string="Detail Bahan Baku",
        copy=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Transfer Dibuat"),
            ("done", "Selesai"),
            ("cancel", "Dibatalkan"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfer Inventory",
        readonly=True,
        copy=False,
    )
    picking_state = fields.Selection(
        related="picking_id.state",
        string="Status Transfer",
        readonly=True,
    )
    notes = fields.Text(string="Catatan")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("raw.material.usage.document") or _("New")
        return super().create(vals_list)

    def action_confirm(self):
        for usage in self:
            if usage.picking_id:
                raise UserError(_("Transfer inventory untuk dokumen ini sudah dibuat."))
            if not usage.spk_reference:
                raise UserError(_("Referensi SPK wajib diisi."))
            if not usage.line_ids:
                raise UserError(_("Minimal isi satu bahan baku untuk pemakaian."))

            usage.line_ids._validate_lines()
            usage._check_stock_availability()
            usage.picking_id = usage._create_stock_picking()
            usage.state = "confirmed"

    def action_validate_usage(self):
        for usage in self:
            if not usage.picking_id:
                usage.action_confirm()

            picking = usage.picking_id
            if picking.state == "done":
                usage.state = "done"
                continue
            if picking.state == "cancel":
                raise UserError(_("Transfer inventory sudah dibatalkan."))

            usage._check_stock_availability()
            picking.action_assign()
            for move in picking.move_ids:
                if "quantity" in move._fields:
                    move.quantity = move.product_uom_qty
                elif "quantity_done" in move._fields:
                    move.quantity_done = move.product_uom_qty

            result = picking.button_validate()
            if isinstance(result, dict) and result.get("res_model") == "stock.immediate.transfer":
                self.env[result["res_model"]].browse(result["res_id"]).process()

            usage.action_sync_state()

    def action_sync_state(self):
        for usage in self:
            if not usage.picking_id:
                continue
            if usage.picking_id.state == "done":
                usage.state = "done"
            elif usage.picking_id.state == "cancel":
                usage.state = "cancel"

    def action_cancel(self):
        for usage in self:
            if usage.picking_id and usage.picking_id.state not in ("done", "cancel"):
                usage.picking_id.action_cancel()
            usage.state = "cancel"

    def action_view_picking(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Transfer Inventory"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": self.picking_id.id,
        }

    def _create_stock_picking(self):
        self.ensure_one()
        picking_type = self.env.ref(
            "raw_material_inventory.picking_type_raw_material_usage",
            raise_if_not_found=False,
        )
        source_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        destination_location = self.env.ref(
            "raw_material_inventory.stock_location_raw_material_production",
            raise_if_not_found=False,
        )
        if not picking_type or not source_location or not destination_location:
            raise UserError(_("Konfigurasi lokasi atau operation type bahan baku belum lengkap."))

        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source_location.id,
            "location_dest_id": destination_location.id,
            "origin": self.name,
            "scheduled_date": self.date,
            "is_raw_material_usage": True,
            "spk_reference": self.spk_reference,
            "move_ids": [
                (0, 0, line._prepare_stock_move_values(source_location, destination_location))
                for line in self.line_ids
            ],
        })
        picking.action_confirm()
        return picking

    def _check_stock_availability(self):
        source_location = self._get_source_location()
        for usage in self:
            required_by_product = usage._get_required_quantities_by_product()
            self._check_required_quantities_available(required_by_product, source_location)

    def _get_source_location(self):
        source_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        if not source_location:
            raise UserError(_("Lokasi stok bahan baku belum dikonfigurasi."))
        return source_location

    def _get_required_quantities_by_product(self):
        self.ensure_one()
        required_by_product = defaultdict(float)
        for line in self.line_ids:
            if not line.product_id:
                continue
            quantity = line.quantity
            if line.product_uom_id and line.product_uom_id != line.product_id.uom_id:
                quantity = line.product_uom_id._compute_quantity(quantity, line.product_id.uom_id)
            required_by_product[line.product_id.id] += quantity
        return required_by_product

    @api.model
    def _check_required_quantities_available(self, required_by_product, source_location):
        if not required_by_product:
            return

        products = self.env["product.product"].browse(list(required_by_product.keys())).exists()
        available_by_product = self._get_available_quantities_by_product(products, source_location)
        shortage_messages = []

        for product in products:
            required_qty = required_by_product.get(product.id, 0.0)
            available_qty = available_by_product.get(product.id, 0.0)
            precision_rounding = product.uom_id.rounding
            if (
                float_compare(
                    required_qty,
                    available_qty,
                    precision_rounding=precision_rounding,
                )
                <= 0
            ):
                continue

            shortage_messages.append(
                _(
                    "%(product)s: diminta %(required).2f %(uom)s, "
                    "stok tersedia %(available).2f %(uom)s"
                ) % {
                    "product": product.display_name,
                    "required": required_qty,
                    "available": available_qty,
                    "uom": product.uom_id.name,
                }
            )

        if shortage_messages:
            raise UserError(
                _("Stok bahan baku tidak mencukupi:\n%s")
                % "\n".join(shortage_messages)
            )

    @api.model
    def _get_available_quantities_by_product(self, products, source_location):
        quantities_by_product = dict.fromkeys(products.ids, 0.0)
        if not products:
            return quantities_by_product

        groups = self.env["stock.quant"].sudo().read_group(
            [
                ("product_id", "in", products.ids),
                ("location_id", "child_of", source_location.id),
            ],
            ["product_id", "quantity:sum"],
            ["product_id"],
        )
        for group in groups:
            product_id = group["product_id"][0]
            quantities_by_product[product_id] = group.get("quantity", 0.0)
        return quantities_by_product


class RawMaterialUsageLine(models.Model):
    _name = "raw.material.usage.line"
    _description = "Raw Material Usage Line"

    usage_id = fields.Many2one(
        "raw.material.usage",
        string="Pemakaian Bahan Baku",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Bahan Baku",
        required=True,
        domain=[("product_tmpl_id.is_raw_material", "=", True)],
    )
    quantity = fields.Float(
        string="Jumlah",
        required=True,
        digits="Product Unit of Measure",
        default=1.0,
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Satuan",
        related="product_id.uom_id",
        readonly=True,
    )
    notes = fields.Char(string="Catatan")

    @api.constrains("product_id", "quantity")
    def _check_product_and_quantity(self):
        self._validate_lines()

    def _validate_lines(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Jumlah pemakaian bahan baku harus lebih dari 0."))
            if line.product_id and not line.product_id.product_tmpl_id.is_raw_material:
                raise ValidationError(
                    _("Produk %s belum ditandai sebagai bahan baku.")
                    % line.product_id.display_name
                )

    def _prepare_stock_move_values(self, source_location, destination_location):
        self.ensure_one()
        return {
            "name": self.product_id.display_name,
            "product_id": self.product_id.id,
            "product_uom_qty": self.quantity,
            "product_uom": self.product_uom_id.id,
            "location_id": source_location.id,
            "location_dest_id": destination_location.id,
            "description_picking": self.notes or self.usage_id.spk_reference,
        }

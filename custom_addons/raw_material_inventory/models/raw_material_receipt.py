from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RawMaterialReceipt(models.Model):
    _name = "raw.material.receipt"
    _description = "Raw Material Receipt"
    _order = "date desc, id desc"

    name = fields.Char(
        string="Nomor Dokumen",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    date = fields.Datetime(
        string="Tanggal Penerimaan",
        required=True,
        default=fields.Datetime.now,
    )
    supplier_reference = fields.Char(string="Referensi Supplier")
    line_ids = fields.One2many(
        "raw.material.receipt.line",
        "receipt_id",
        string="Detail Bahan Baku",
        copy=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Receipt Dibuat"),
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
        string="Receipt Inventory",
        readonly=True,
        copy=False,
    )
    picking_state = fields.Selection(
        related="picking_id.state",
        string="Status Receipt",
        readonly=True,
    )
    notes = fields.Text(string="Catatan")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("raw.material.receipt.document") or _("New")
        return super().create(vals_list)

    def action_confirm(self):
        for receipt in self:
            if receipt.picking_id:
                raise UserError(_("Receipt inventory untuk dokumen ini sudah dibuat."))
            if not receipt.line_ids:
                raise UserError(_("Minimal isi satu bahan baku untuk penerimaan."))

            receipt.line_ids._validate_lines()
            receipt.picking_id = receipt._create_stock_picking()
            receipt.state = "confirmed"

    def action_validate_receipt(self):
        for receipt in self:
            if not receipt.picking_id:
                receipt.action_confirm()

            picking = receipt.picking_id
            if picking.state == "done":
                receipt.state = "done"
                continue
            if picking.state == "cancel":
                raise UserError(_("Receipt inventory sudah dibatalkan."))

            for move in picking.move_ids:
                if "quantity" in move._fields:
                    move.quantity = move.product_uom_qty
                elif "quantity_done" in move._fields:
                    move.quantity_done = move.product_uom_qty

            result = picking.button_validate()
            if isinstance(result, dict) and result.get("res_model") == "stock.immediate.transfer":
                self.env[result["res_model"]].browse(result["res_id"]).process()

            receipt.action_sync_state()

    def action_sync_state(self):
        for receipt in self:
            if not receipt.picking_id:
                continue
            if receipt.picking_id.state == "done":
                receipt.state = "done"
            elif receipt.picking_id.state == "cancel":
                receipt.state = "cancel"

    def action_cancel(self):
        for receipt in self:
            if receipt.picking_id and receipt.picking_id.state not in ("done", "cancel"):
                receipt.picking_id.action_cancel()
            receipt.state = "cancel"

    def action_view_picking(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Receipt Inventory"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": self.picking_id.id,
        }

    def _create_stock_picking(self):
        self.ensure_one()
        picking_type = self.env["stock.picking.type"].search([
            ("code", "=", "incoming"),
            ("warehouse_id.company_id", "in", [False, self.env.company.id]),
        ], limit=1)
        supplier_location = self.env.ref("stock.stock_location_suppliers", raise_if_not_found=False)
        stock_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        if not picking_type or not supplier_location or not stock_location:
            raise UserError(_("Konfigurasi receipt, lokasi supplier, atau lokasi stok belum lengkap."))

        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": supplier_location.id,
            "location_dest_id": stock_location.id,
            "origin": self.supplier_reference or self.name,
            "scheduled_date": self.date,
            "move_ids": [
                (0, 0, line._prepare_stock_move_values(supplier_location, stock_location))
                for line in self.line_ids
            ],
        })
        picking.action_confirm()
        picking.action_assign()
        return picking


class RawMaterialReceiptLine(models.Model):
    _name = "raw.material.receipt.line"
    _description = "Raw Material Receipt Line"

    receipt_id = fields.Many2one(
        "raw.material.receipt",
        string="Penerimaan Bahan Baku",
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
        string="Jumlah Diterima",
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
                raise ValidationError(_("Jumlah penerimaan bahan baku harus lebih dari 0."))
            if line.product_id and not line.product_id.product_tmpl_id.is_raw_material:
                raise ValidationError(
                    _("Produk %s belum ditandai sebagai bahan baku.")
                    % line.product_id.display_name
                )

    def _prepare_stock_move_values(self, supplier_location, stock_location):
        self.ensure_one()
        return {
            "name": self.product_id.display_name,
            "product_id": self.product_id.id,
            "product_uom_qty": self.quantity,
            "product_uom": self.product_uom_id.id,
            "location_id": supplier_location.id,
            "location_dest_id": stock_location.id,
            "description_picking": self.notes or self.receipt_id.supplier_reference,
        }

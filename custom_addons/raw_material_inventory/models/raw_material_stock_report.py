from odoo import _, fields, models
from odoo.exceptions import UserError


class RawMaterialStockReportWizard(models.TransientModel):
    _name = "raw.material.stock.report.wizard"
    _description = "Raw Material Stock Report Wizard"

    report_scope = fields.Selection(
        [
            ("all", "Seluruh Bahan"),
            ("critical", "Bahan Kritis"),
            ("specific", "Bahan Tertentu"),
        ],
        string="Parameter Laporan",
        default="all",
        required=True,
    )
    product_ids = fields.Many2many(
        "product.template",
        string="Bahan Baku",
        domain=[("is_raw_material", "=", True)],
    )
    date_from = fields.Date(string="Dari Tanggal")
    date_to = fields.Date(string="Sampai Tanggal")

    def action_view_report(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_("Dari Tanggal tidak boleh lebih besar dari Sampai Tanggal."))

        domain = [("is_raw_material", "=", True)]
        report_name = _("Laporan Stok Bahan Baku")

        if self.report_scope == "critical":
            domain.append(("is_stock_critical", "=", True))
            report_name = _("Laporan Stok Bahan Baku Kritis")
        elif self.report_scope == "specific":
            if not self.product_ids:
                raise UserError(_("Pilih minimal satu bahan baku untuk laporan bahan tertentu."))
            domain.append(("id", "in", self.product_ids.ids))
            report_name = _("Laporan Stok Bahan Baku Tertentu")

        products = self.env["product.template"].search(domain)
        self.env["raw.material.stock.report.line"].search([
            ("create_uid", "=", self.env.uid),
        ]).unlink()
        report_lines = self._prepare_report_lines(products)
        if not report_lines:
            raise UserError(_("Tidak ada bahan baku yang sesuai dengan parameter laporan."))

        lines = self.env["raw.material.stock.report.line"].create(report_lines)
        return {
            "type": "ir.actions.act_window",
            "name": report_name,
            "res_model": "raw.material.stock.report.line",
            "view_mode": "tree",
            "domain": [("id", "in", lines.ids)],
            "context": {"create": False, "edit": False, "delete": False},
            "views": [
                (self.env.ref("raw_material_inventory.view_raw_material_stock_report_line_tree").id, "tree"),
            ],
        }

    def _prepare_report_lines(self, products):
        lines = []
        movements_by_product = self._get_stock_movements(products)

        for product in products:
            variant = product.product_variant_id
            movements = movements_by_product.get(variant.id, [])
            current_qty = variant.qty_available
            period_net_qty = sum(
                movement["received_qty"] - movement["used_qty"]
                for movement in movements
            )
            balance_qty = current_qty - period_net_qty

            lines.append({
                "product_tmpl_id": product.id,
                "product_id": variant.id,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "movement_date": self._get_opening_movement_date(),
                "movement_type": "opening",
                "document_name": _("Stok Awal Periode"),
                "opening_qty": balance_qty,
                "received_qty": 0.0,
                "used_qty": 0.0,
                "net_qty": 0.0,
                "balance_qty": balance_qty,
                "current_qty": current_qty,
                "forecast_qty": variant.virtual_available,
                "reorder_point": product.raw_material_reorder_point,
                "stock_status": product.raw_material_stock_status,
            })

            for movement in movements:
                balance_qty += movement["received_qty"] - movement["used_qty"]
                lines.append({
                    "product_tmpl_id": product.id,
                    "product_id": variant.id,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "movement_date": movement["movement_date"],
                    "movement_type": movement["movement_type"],
                    "document_name": movement["document_name"],
                    "reference": movement["reference"],
                    "opening_qty": 0.0,
                    "received_qty": movement["received_qty"],
                    "used_qty": movement["used_qty"],
                    "net_qty": movement["received_qty"] - movement["used_qty"],
                    "balance_qty": balance_qty,
                    "current_qty": current_qty,
                    "forecast_qty": variant.virtual_available,
                    "reorder_point": product.raw_material_reorder_point,
                    "stock_status": product.raw_material_stock_status,
                })

        return lines

    def _get_stock_movements(self, products):
        movements_by_product = {product.product_variant_id.id: [] for product in products}

        receipt_domain = self._get_movement_domain(
            "receipt_id",
            products,
        )
        usage_domain = self._get_movement_domain(
            "usage_id",
            products,
        )

        for line in self.env["raw.material.receipt.line"].search(receipt_domain):
            movements_by_product.setdefault(line.product_id.id, []).append({
                "movement_date": line.receipt_id.date,
                "movement_type": "receipt",
                "document_name": line.receipt_id.name,
                "reference": line.receipt_id.supplier_reference,
                "received_qty": line.quantity,
                "used_qty": 0.0,
            })

        for line in self.env["raw.material.usage.line"].search(usage_domain):
            movements_by_product.setdefault(line.product_id.id, []).append({
                "movement_date": line.usage_id.date,
                "movement_type": "usage",
                "document_name": line.usage_id.name,
                "reference": line.usage_id.spk_reference,
                "received_qty": 0.0,
                "used_qty": line.quantity,
            })

        for movements in movements_by_product.values():
            movements.sort(key=lambda movement: (
                movement["movement_date"] or fields.Datetime.now(),
                movement["movement_type"],
                movement["document_name"] or "",
            ))

        return movements_by_product

    def _get_movement_domain(self, parent_field, products):
        domain = [
            ("%s.state" % parent_field, "=", "done"),
            ("product_id.product_tmpl_id", "in", products.ids),
        ]
        if self.date_from:
            domain.append((
                "%s.date" % parent_field,
                ">=",
                fields.Datetime.to_datetime(self.date_from),
            ))
        if self.date_to:
            domain.append((
                "%s.date" % parent_field,
                "<=",
                fields.Datetime.to_datetime(self.date_to).replace(
                    hour=23,
                    minute=59,
                    second=59,
                ),
            ))
        return domain

    def _get_opening_movement_date(self):
        if self.date_from:
            return fields.Datetime.to_datetime(self.date_from)
        return False


class RawMaterialStockReportLine(models.TransientModel):
    _name = "raw.material.stock.report.line"
    _description = "Raw Material Stock Report Line"
    _order = "product_tmpl_id, movement_date, id"

    product_tmpl_id = fields.Many2one("product.template", string="Bahan Baku", readonly=True)
    product_id = fields.Many2one("product.product", string="Varian", readonly=True)
    default_code = fields.Char(
        string="Kode",
        related="product_tmpl_id.default_code",
        readonly=True,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Satuan",
        related="product_tmpl_id.uom_id",
        readonly=True,
    )
    date_from = fields.Date(string="Dari Tanggal", readonly=True)
    date_to = fields.Date(string="Sampai Tanggal", readonly=True)
    movement_date = fields.Datetime(string="Tanggal Mutasi", readonly=True)
    movement_type = fields.Selection(
        [
            ("opening", "Stok Awal"),
            ("receipt", "Penerimaan"),
            ("usage", "Pemakaian"),
        ],
        string="Jenis",
        readonly=True,
    )
    document_name = fields.Char(string="Dokumen", readonly=True)
    reference = fields.Char(string="Referensi", readonly=True)
    opening_qty = fields.Float(
        string="Stok Awal Periode",
        digits="Product Unit of Measure",
        readonly=True,
    )
    received_qty = fields.Float(
        string="Masuk",
        digits="Product Unit of Measure",
        readonly=True,
    )
    used_qty = fields.Float(
        string="Keluar/Pemakaian",
        digits="Product Unit of Measure",
        readonly=True,
    )
    net_qty = fields.Float(
        string="Selisih",
        digits="Product Unit of Measure",
        readonly=True,
    )
    balance_qty = fields.Float(
        string="Saldo",
        digits="Product Unit of Measure",
        readonly=True,
    )
    current_qty = fields.Float(
        string="Stok Saat Ini",
        digits="Product Unit of Measure",
        readonly=True,
    )
    forecast_qty = fields.Float(
        string="Forecast",
        digits="Product Unit of Measure",
        readonly=True,
    )
    reorder_point = fields.Float(
        string="Reorder Point",
        digits="Product Unit of Measure",
        readonly=True,
    )
    stock_status = fields.Selection(
        [
            ("safe", "Aman"),
            ("critical", "Kritis"),
        ],
        string="Status",
        readonly=True,
    )

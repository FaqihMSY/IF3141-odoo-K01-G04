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

    def action_view_report(self):
        self.ensure_one()

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

        return {
            "type": "ir.actions.act_window",
            "name": report_name,
            "res_model": "product.template",
            "view_mode": "tree,form",
            "domain": domain,
            "context": {
                "default_is_raw_material": True,
                "default_detailed_type": "product",
            },
            "views": [
                (self.env.ref("raw_material_inventory.view_raw_material_stock_report_tree").id, "tree"),
                (self.env.ref("raw_material_inventory.view_raw_material_product_form").id, "form"),
            ],
        }

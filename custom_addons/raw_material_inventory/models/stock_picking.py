from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_raw_material_usage = fields.Boolean(
        string="Pemakaian Bahan Baku",
        help="Tandai transfer ini sebagai pencatatan pemakaian bahan baku untuk produksi.",
    )
    spk_reference = fields.Char(string="Referensi SPK")

    def button_validate(self):
        for picking in self:
            if not picking.is_raw_material_usage:
                continue
            if not picking.spk_reference:
                raise UserError(_("Referensi SPK wajib diisi untuk pemakaian bahan baku."))

            invalid_moves = picking.move_ids.filtered(
                lambda move: move.product_id
                and not move.product_id.product_tmpl_id.is_raw_material
            )
            if invalid_moves:
                product_names = ", ".join(invalid_moves.mapped("product_id.display_name"))
                raise UserError(
                    _("Produk berikut belum ditandai sebagai bahan baku: %s") % product_names
                )

        result = super().button_validate()

        usages = self.env["raw.material.usage"].search([("picking_id", "in", self.ids)])
        for usage in usages:
            if usage.picking_id.state == "done":
                usage.state = "done"

        return result

    def action_cancel(self):
        result = super().action_cancel()

        usages = self.env["raw.material.usage"].search([("picking_id", "in", self.ids)])
        usages.write({"state": "cancel"})

        return result

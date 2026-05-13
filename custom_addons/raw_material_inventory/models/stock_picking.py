from collections import defaultdict

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
            picking._check_raw_material_usage_stock_availability()

        result = super().button_validate()

        usages = self.env["raw.material.usage"].search([("picking_id", "in", self.ids)])
        for usage in usages:
            if usage.picking_id.state == "done":
                usage.state = "done"

        return result

    def _check_raw_material_usage_stock_availability(self):
        usage_model = self.env["raw.material.usage"]
        for picking in self:
            required_by_product = defaultdict(float)
            active_moves = picking.move_ids.filtered(
                lambda stock_move: stock_move.state not in ("cancel", "done")
            )
            for move in active_moves:
                if not move.product_id:
                    continue

                quantity = move.product_uom_qty
                if "quantity" in move._fields and move.quantity:
                    quantity = move.quantity
                elif "quantity_done" in move._fields and move.quantity_done:
                    quantity = move.quantity_done
                if move.product_uom and move.product_uom != move.product_id.uom_id:
                    quantity = move.product_uom._compute_quantity(
                        quantity,
                        move.product_id.uom_id,
                    )

                required_by_product[move.product_id.id] += quantity

            usage_model._check_required_quantities_available(
                required_by_product,
                picking.location_id,
            )

    def action_cancel(self):
        result = super().action_cancel()

        usages = self.env["raw.material.usage"].search([("picking_id", "in", self.ids)])
        usages.write({"state": "cancel"})

        return result

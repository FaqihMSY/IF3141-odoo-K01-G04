import logging

from odoo import models


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        result = super().button_validate()

        sale_orders = self.filtered(
            lambda picking: picking.picking_type_code == "outgoing"
            and picking.state == "done"
            and picking.sale_id
        ).mapped("sale_id")
        try:
            sale_orders._fr06_create_and_post_invoice()
        except Exception:
            _logger.exception("FR-06 automatic invoice generation failed after delivery.")

        return result

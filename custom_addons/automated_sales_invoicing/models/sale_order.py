import logging

from odoo import _, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    auto_invoice_id = fields.Many2one(
        "account.move",
        string="Automatic Invoice",
        copy=False,
        readonly=True,
    )
    auto_invoice_created = fields.Boolean(
        string="Automatic Invoice Created",
        copy=False,
        readonly=True,
    )
    auto_invoice_date = fields.Datetime(
        string="Automatic Invoice Date",
        copy=False,
        readonly=True,
    )

    def _has_completed_delivery_for_auto_invoice(self):
        self.ensure_one()
        outgoing_pickings = self.picking_ids.filtered(
            lambda picking: picking.picking_type_code == "outgoing"
            and picking.state != "cancel"
        )
        return bool(outgoing_pickings) and all(
            picking.state == "done" for picking in outgoing_pickings
        )

    def _is_ready_for_auto_invoice(self):
        self.ensure_one()
        existing_invoice = self.auto_invoice_id
        if existing_invoice and existing_invoice.state != "cancel":
            return False

        return (
            self.state in ("sale", "done")
            and self.invoice_status == "to invoice"
            and self._has_completed_delivery_for_auto_invoice()
        )

    def _create_and_post_automatic_invoice(self):
        ready_orders = self.filtered(lambda order: order._is_ready_for_auto_invoice())
        created_invoices = self.env["account.move"]

        for order in ready_orders:
            invoices = order._create_invoices()
            invoices = invoices.filtered(lambda move: move.move_type == "out_invoice")

            if not invoices:
                continue

            invoices.write({"auto_invoice_generated": True})
            draft_invoices = invoices.filtered(lambda move: move.state == "draft")
            draft_invoices.action_post()

            invoice = invoices[:1]
            order.write(
                {
                    "auto_invoice_id": invoice.id,
                    "auto_invoice_created": True,
                    "auto_invoice_date": fields.Datetime.now(),
                }
            )
            created_invoices |= invoices

        return created_invoices

    def action_create_automatic_invoice(self):
        invoices = self._create_and_post_automatic_invoice()
        if not invoices:
            raise UserError(
                _(
                    "No invoice was created. Make sure the sales order is confirmed, "
                    "all related delivery orders are done, and there is something to invoice."
                )
            )

        if len(invoices) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Customer Invoice"),
                "res_model": "account.move",
                "res_id": invoices.id,
                "view_mode": "form",
            }

        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoices"),
            "res_model": "account.move",
            "domain": [("id", "in", invoices.ids)],
            "view_mode": "tree,form",
        }

    def _cron_auto_invoice_ready_orders(self, limit=50):
        orders = self.search(
            [
                ("state", "in", ("sale", "done")),
                ("invoice_status", "=", "to invoice"),
                "|",
                ("auto_invoice_id", "=", False),
                ("auto_invoice_id.state", "=", "cancel"),
            ],
            limit=limit,
        )

        ready_orders = orders.filtered(lambda order: order._is_ready_for_auto_invoice())
        try:
            ready_orders._create_and_post_automatic_invoice()
        except Exception:
            _logger.exception("Automatic invoice generation failed.")
            raise

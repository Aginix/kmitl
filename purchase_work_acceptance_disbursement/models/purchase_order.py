# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pending_wa_count = fields.Integer(
        compute="_compute_pending_wa_count",
    )

    wa_fines_total = fields.Monetary(
        string="Amount disbursed",
        compute="_compute_wa_fines_total",
        currency_field="currency_id",
    )

    @api.depends("order_line.wa_line_ids.wa_id.state", "order_line.wa_line_ids.wa_id.is_disbursed", "order_line.wa_line_ids.wa_id.fines_total")
    def _compute_wa_fines_total(self):
        for order in self:
            was = self.env["work.acceptance"].search([
                ("purchase_id", "=", order.id),
                ("state", "=", "accept"),
                ("is_disbursed", "=", True),
            ])
            order.wa_fines_total = sum(was.mapped("fines_total"))

    @api.depends("order_line.wa_line_ids.wa_id.state", "order_line.wa_line_ids.wa_id.is_disbursed")
    def _compute_pending_wa_count(self):
        for order in self:
            order.pending_wa_count = self.env["work.acceptance"].search_count([
                ("purchase_id", "=", order.id),
                ("is_disbursed", "=", False),
                ("state", "=", "accept"),
            ])

    def _get_pending_wa(self):
        """คืน WA ใบเดียวที่ accept แล้วและยังไม่ถูก disburse"""
        self.ensure_one()
        return self.env["work.acceptance"].search([
            ("purchase_id", "=", self.id),
            ("state", "=", "accept"),
            ("is_disbursed", "=", False),
        ], order="date_accept asc", limit=1)

    def _prepare_disbursement_request_vals(self):
        """Override: ใช้ WA lines แทน PO lines"""
        vals = super()._prepare_disbursement_request_vals()
        wa = self._get_pending_wa()
        if not wa:
            return vals
        vals["line_ids"] = [
            Command.create({
                **line._prepare_disbursement_line_vals(),
                "partner_id": self.partner_id.id,
            })
            for line in wa.wa_line_ids
        ]
        return vals

    def _create_disbursement_request(self):
        wa = self._get_pending_wa()
        if not wa:
            raise UserError(
                _("No accepted Work Acceptance pending disbursement for PO '%s'.")
                % self.name
            )
        disbursement = super()._create_disbursement_request()
        wa._link_to_disbursement(
            disbursement,
            analytic_distribution=self.analytic_distribution or False,
            fine_tax_ids=self.order_line.taxes_id.ids,
        )
        return disbursement

    @api.depends(
        "state",
        "is_disbursement_request_allowed",
        "disbursement_request_ids.state",
        "pending_wa_count",
    )
    def _compute_hide_create_disbursement_request_button(self):
        for order in self:
            has_unfinished_disbursement = any(
                d.state in ("draft", "submitted")
                for d in order.disbursement_request_ids
            )
            order.hide_create_disbursement_request_button = (
                order.state != "purchase"
                or not order.is_disbursement_request_allowed
                or order.pending_wa_count == 0
                or has_unfinished_disbursement
            )

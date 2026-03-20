# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pending_wa_count = fields.Integer(
        compute="_compute_pending_wa_count",
    )

    @api.depends("wa_ids.state", "wa_ids.is_disbursed")
    def _compute_pending_wa_count(self):
        for order in self:
            order.pending_wa_count = self.env["work.acceptance"].search_count([
                ("purchase_id", "=", order.id),
                ("is_disbursed", "=", False),
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
            Command.create(line._prepare_disbursement_line_vals())
            for line in wa.wa_line_ids
        ]
        return vals

    def _create_disbursement_request(self):
        """Override: link WA หลังสร้าง disbursement"""
        wa = self._get_pending_wa()
        if not wa:
            raise UserError(
                _("No accepted Work Acceptance pending disbursement for PO '%s'.")
                % self.name
            )

        disbursement = super()._create_disbursement_request()

        wa.write({"disbursement_request_id": disbursement.id})

        # Log cross-links
        dr_link = "/web#id=%d&model=disbursement.request&view_type=form" % disbursement.id
        wa.message_post(
            body=_(
                'Disbursement Request <a href="%(link)s">%(name)s</a> created.'
            ) % {"link": dr_link, "name": disbursement.name},
            subtype_xmlid="mail.mt_note",
        )

        return disbursement

    def _compute_hide_create_disbursement_request_button(self):
        """Override: แสดงปุ่มเมื่อ state=purchase และมี pending WA"""
        for order in self:
            order.hide_create_disbursement_request_button = (
                order.state != "purchase" or not order._get_pending_wa()
            )

    @api.depends(
        "state",
        "is_disbursement_request_allowed",
        "disbursement_request_ids.state",
        "wa_ids.is_disbursed",
        "wa_ids.state",
    )
    def _compute_hide_create_disbursement_request_button(self):
        for order in self:
            has_pending_wa = bool(order.wa_ids.filtered(
                lambda w: w.state == "accept" and not w.is_disbursed
            ))
            has_unfinished_disbursement = bool(order.disbursement_request_ids.filtered(
                lambda d: d.state not in ("validated", "cancel")
            ))

            order.hide_create_disbursement_request_button = (
                order.state != "purchase"
                or not order.is_disbursement_request_allowed
                or not has_pending_wa
                or has_unfinished_disbursement
            )

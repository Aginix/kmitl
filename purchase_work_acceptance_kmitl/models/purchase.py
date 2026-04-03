# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    wa_tier_validation = fields.Boolean(
        string="Paperless WA",
        default=True,
        help="If checked, WA created will be approved by committee by tier valiation."
        "Each committee will be notified (by email or inbox) to approve WA.\n"
        "If not checked, WA will be approved by paper outside Odoo, "
        "and the result of WA will be filled in by procurement officer",
    )

    wa_fines_total = fields.Monetary(
        string="Amount disbursed",
        compute="_compute_wa_fines_total",
        currency_field="currency_id",
    )

    @api.depends("wa_ids.state", "wa_ids.is_disbursed", "wa_ids.fines_late")
    def _compute_wa_fines_total(self):
        for order in self:
            was = self.env["work.acceptance"].search([
                ("purchase_id", "=", order.id),
                ("state", "=", "accept"),
                ("is_disbursed", "=", True),
            ])
            order.wa_fines_total = sum(was.mapped("fines_late"))

    def _prepare_committee_line(self, line):
        return {
            "employee_id": line.employee_id.id,
            "name": line.name,
            "approve_role": line.approve_role,
            "note": line.note,
        }

    def _get_committee_line(self, purchase_requests):
        committees = purchase_requests.mapped("work_acceptance_committee_ids")
        lines = [(0, 0, self._prepare_committee_line(line)) for line in committees]
        return lines

    def action_view_wa(self):
        result = super().action_view_wa()
        purchase_requests = self.order_line.mapped("purchase_request_lines.request_id")
        lines = self._get_committee_line(purchase_requests)
        result["context"]["default_work_acceptance_committee_ids"] = lines
        result["context"]["default_wa_tier_validation"] = self.wa_tier_validation
        result["context"]["default_late_days"] = self.late_days
        result["context"]["default_fines_rate"] = self.fines_rate
        return result

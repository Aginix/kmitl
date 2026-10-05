# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    wa_tier_validation = fields.Boolean(
        string="Paperless WA",
        default=True,
        help="If checked, WA created will be approved by committee by tier validation."
        "Each committee will be notified (by email or inbox) to approve WA.\n"
        "If not checked, WA will be approved by paper outside Odoo, "
        "and the result of WA will be filled in by procurement officer",
    )

    work_end_original = fields.Date(
        string="Original Work End Date",
        copy=False,
    )

    def button_confirm_manual(self):
        result = super().button_confirm_manual()
        for record in self:
            if not record.work_end_original:
                record.work_end_original = record.work_end
        return result

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
        result["context"]["default_po_date_order_date"] = self.date_order_date
        result["context"]["default_po_work_start"] = self.work_start
        po_lines_by_id = {line.id: line for line in self.order_line}
        for cmd in result["context"].get("default_wa_line_ids", []):
            if cmd[0] == 0 and isinstance(cmd[2], dict):
                po_line = po_lines_by_id.get(cmd[2].get("purchase_line_id"))
                if po_line:
                    cmd[2]["uom_text"] = po_line.uom_text
        return result

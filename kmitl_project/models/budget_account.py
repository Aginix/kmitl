# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    is_project = fields.Boolean(
        string="เป็นโครงการ/กิจกรรม/โครงการยุทธศาสตร์",
        help="หากติ๊กถูก รหัสงบประมาณนี้จะต้องระบุเงินผ่านโครงการ/กิจกรรม/โครงการยุทธศาสตร์เท่านั้น",
        tracking=True,
        default=False,
    )

    project_type = fields.Selection(
        [("project", "Project/Activity"), ("strategic_project", "Strategic Project")],
        tracking=True,
    )

    def _check_project_procurement_exclusive(self):
        """A project budget code follows the floating-budget path — it reserves only
        when its project is confirmed (ADR-0007) — whereas a procurement-plan code
        auto-reserves the moment its appropriation posts (ADR-0005). A code can be at
        most one of the two. Enforced on create/write (not @api.constrains) so it can
        watch the *optional* ``procurement_plan`` field from either direction without
        kmitl_project having to depend on that module — and is a no-op when the field
        is absent."""
        if "procurement_plan" not in self._fields:
            return
        for account in self:
            if account.is_project and account.procurement_plan:
                raise ValidationError(
                    _(
                        "รหัสงบประมาณ %s กำหนดเป็นได้อย่างใดอย่างหนึ่งเท่านั้น "
                        "ระหว่าง 'โครงการ/กิจกรรม' กับ 'แผนจัดซื้อจัดจ้าง'"
                    )
                    % account.display_name
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_project_procurement_exclusive()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "is_project" in vals or "procurement_plan" in vals:
            self._check_project_procurement_exclusive()
        return res

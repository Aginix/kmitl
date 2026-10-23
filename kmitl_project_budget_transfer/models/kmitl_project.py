from odoo import _, api, fields, models
from odoo.exceptions import UserError

# From ส่งเข้าแผน (the analytic exists) until the project closes (ADR-0009).
FLOATING_ALLOCATION_STATES = ("to_verify", "to_send", "sent", "returned", "in_progress")
# Money may go back whenever the project has an analytic, except while the
# ขออนุมัติ หนังสือ quotes the budget (ADR-0011).
FLOATING_RETURN_STATES = (
    "draft",
    "to_verify",
    "returned",
    "rejected",
    "in_progress",
    "complete",
    "cancel",
)


class KmitlProject(models.Model):
    """A project another unit may fund (ADR-0008).

    A project's ``kmitl_project`` analytic is minted scoped to the project's
    operating unit, so other units cannot pick it on a budget transfer. Ticking
    the flag clears that scope — the analytic becomes visible system-wide — so a
    supporting unit can transfer budget INTO the project's own coordinate.
    Unticking restores the owning unit's scope.
    """

    _inherit = "kmitl.project"

    is_supported_by_other_units = fields.Boolean(
        string="มีการสนับสนุนจากหน่วยงานอื่น",
        tracking=True,
        copy=False,
        help="ติ๊กเมื่อโครงการนี้ได้รับการสนับสนุนงบประมาณจากหน่วยงานอื่น — "
        "มิติโครงการ (analytic account) จะเปิดให้ทุกหน่วยงานมองเห็น "
        "เพื่อให้หน่วยงานผู้สนับสนุนเลือกโครงการนี้เป็นปลายทางในใบโอนงบประมาณได้ "
        "เอาติ๊กออกเพื่อจำกัดให้เห็นเฉพาะหน่วยงานเจ้าของโครงการตามเดิม",
    )

    @api.model
    def _create_analytic_account_from_values(self, values):
        analytic = super()._create_analytic_account_from_values(values)
        if self.is_supported_by_other_units:
            analytic.sudo().operating_unit_ids = [(5, 0, 0)]
        return analytic

    def write(self, vals):
        res = super().write(vals)
        if {"is_supported_by_other_units", "operating_unit_id"} & set(vals):
            self._sync_analytic_operating_units()
        return res

    def _sync_analytic_operating_units(self):
        """Open a supported project's analytic to every unit, else scope it to
        the project's own operating unit."""
        for project in self.filtered("analytic_account_id"):
            if project.is_supported_by_other_units:
                command = [(5, 0, 0)]
            else:
                command = [(6, 0, project.operating_unit_id.ids)]
            project.analytic_account_id.sudo().operating_unit_ids = command

    # ------------------------------------------------------------------
    # Held money: transfers still on their way (ADR-0011)
    # ------------------------------------------------------------------
    def _has_pending_project_transfer(self):
        if super()._has_pending_project_transfer():
            return True
        if not self.analytic_account_id:
            return False
        return bool(
            self.env["budget.transfer"]
            .sudo()
            .search_count(
                [
                    # Not just draft/submitted: verify/e-Saraban bridges add
                    # to_verify, sent and returned on the way to posting.
                    ("state", "not in", ("posted", "cancelled", "rejected")),
                    (
                        "line_ids.kmitl_project_analytic_id",
                        "=",
                        self.analytic_account_id.id,
                    ),
                ]
            )
        )

    # ------------------------------------------------------------------
    # จัดสรรงบประมาณ (งบลอย) / โอนคืนงบลอย
    # ------------------------------------------------------------------
    def _check_budget_user(self):
        if not (
            self.env.user.has_group("budget.group_budget_user") or self.env.is_admin()
        ):
            raise UserError(
                _("เฉพาะเจ้าหน้าที่งบประมาณ (Budget User) เท่านั้นที่โอนงบประมาณโครงการได้")
            )

    def _check_floating_allocation_allowed(self):
        self.ensure_one()
        self._check_budget_user()
        if self.state not in FLOATING_ALLOCATION_STATES or not self.analytic_account_id:
            raise UserError(
                _("จัดสรรงบประมาณ (งบลอย) ได้ตั้งแต่ส่งเข้าแผนจนถึงระหว่างดำเนินโครงการ")
            )
        if not self.budget_account_id:
            raise UserError(_("กรุณาระบุรหัสงบประมาณของโครงการก่อน"))

    def action_open_floating_allocation(self):
        """Open the จัดสรรงบประมาณ (งบลอย) wizard (ADR-0009)."""
        self._check_floating_allocation_allowed()
        return {
            "type": "ir.actions.act_window",
            "name": _("จัดสรรงบประมาณ (งบลอย)"),
            "res_model": "kmitl.project.floating.allocation",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def _check_floating_return_allowed(self):
        self.ensure_one()
        self._check_budget_user()
        if self.state in ("to_send", "sent"):
            raise UserError(
                _(
                    "ไม่สามารถโอนคืนงบลอยขณะยืนยันงบประมาณ/ส่งหนังสือขออนุมัติแล้ว "
                    "กรุณาดึงกลับหรือตีกลับก่อน"
                )
            )
        if self.state not in FLOATING_RETURN_STATES or not self.analytic_account_id:
            raise UserError(_("โครงการนี้ยังไม่มีมิติโครงการ จึงไม่มีเงินให้โอนคืน"))

    def action_open_floating_return(self):
        """Open the โอนคืนงบลอย wizard (ADR-0011)."""
        self._check_floating_return_allowed()
        return {
            "type": "ir.actions.act_window",
            "name": _("โอนคืนงบลอย"),
            "res_model": "kmitl.project.floating.return",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

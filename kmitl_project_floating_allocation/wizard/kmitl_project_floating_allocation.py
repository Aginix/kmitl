from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

# The four core dimensions, in the order the cards show them.
_CORE_DIMS = (
    "department_analytic_id",
    "source_analytic_id",
    "fund_analytic_id",
    "activity_analytic_id",
)


class KmitlProjectFloatingAllocation(models.TransientModel):
    """จัดสรรงบประมาณ (งบลอย) — a Direct Floating Allocation (ADR-0009).

    Three steps in one dialog, like a bank-app transfer: ``input`` (from the
    floating pool → to the project, type the amount), ``review`` and ``done``
    (the slip). Confirming builds a real ``budget.transfer`` FROM the single pool
    covering the project's coordinate TO the project's own dimension, runs the
    ordinary ยืนยัน checks, then posts it at once — no approval, no หนังสือ.
    """

    _name = "kmitl.project.floating.allocation"
    _description = "จัดสรรงบประมาณ (งบลอย)"

    project_id = fields.Many2one("kmitl.project", required=True)
    step = fields.Selection(
        [("input", "กรอกจำนวนเงิน"), ("review", "ตรวจสอบ"), ("done", "สำเร็จ")],
        default="input",
        required=True,
    )
    amount = fields.Float(string="จำนวนเงิน", digits="Budget Precision")
    note = fields.Char(string="บันทึกช่วยจำ")
    transfer_id = fields.Many2one("budget.transfer", readonly=True)
    # Snapshot for the slip: a pool drained to 0 no longer resolves after posting.
    posted_pool_label = fields.Char(readonly=True)
    transfer_name = fields.Char(related="transfer_id.name")
    transfer_date = fields.Datetime(related="transfer_id.approval_date")
    transfer_user_id = fields.Many2one(related="transfer_id.approver_id")

    # --- the floating pool (FROM card) -------------------------------------
    pool_found = fields.Boolean(compute="_compute_pool")
    pool_account_id = fields.Many2one("budget.account", compute="_compute_pool")
    pool_department_analytic_id = fields.Many2one(
        "account.analytic.account", compute="_compute_pool"
    )
    pool_source_analytic_id = fields.Many2one(
        "account.analytic.account", compute="_compute_pool"
    )
    pool_fund_analytic_id = fields.Many2one(
        "account.analytic.account", compute="_compute_pool"
    )
    pool_activity_analytic_id = fields.Many2one(
        "account.analytic.account", compute="_compute_pool"
    )
    pool_label = fields.Char(compute="_compute_pool")
    floating_available = fields.Float(
        digits="Budget Precision", compute="_compute_pool"
    )

    # --- the project (TO card) ---------------------------------------------
    project_label = fields.Char(compute="_compute_project_info")
    project_coordinate = fields.Char(compute="_compute_project_info")
    project_received = fields.Float(
        digits="Budget Precision", compute="_compute_project_info"
    )
    plan_total = fields.Float(
        digits="Budget Precision", compute="_compute_project_info"
    )
    commitment_status = fields.Selection(
        [("none", "ยังไม่จองงบ"), ("reserved", "จองงบแล้ว"), ("spending", "เริ่มใช้จ่ายแล้ว")],
        compute="_compute_project_info",
    )

    @staticmethod
    def _coordinate_label(account, analytics):
        parts = [a.display_name for a in analytics if a]
        return " · ".join([account.display_name or ""] + parts)

    def _project_floating_distribution(self, project):
        """The project's coordinate without its own project dimension — where its
        floating money waits."""
        return {str(project[dim].id): 100 for dim in _CORE_DIMS if project[dim]}

    @api.depends("project_id")
    def _compute_pool(self):
        controller = self.env["budget.controller"]
        Analytic = self.env["account.analytic.account"]
        for wiz in self:
            project = wiz.project_id.sudo()
            detail = {"available": 0.0, "pool": None}
            if project.budget_account_id and project.account_fiscal_year_id:
                detail = controller.get_available_detail(
                    project.budget_account_id,
                    self._project_floating_distribution(project),
                    project.account_fiscal_year_id.id,
                    project.company_id.id,
                )
            pool = detail["pool"]
            if not pool:
                wiz.update(
                    {
                        "pool_found": False,
                        "pool_account_id": False,
                        "pool_department_analytic_id": False,
                        "pool_source_analytic_id": False,
                        "pool_fund_analytic_id": False,
                        "pool_activity_analytic_id": False,
                        "pool_label": False,
                        "floating_available": 0.0,
                    }
                )
                continue
            dims = {
                dim: Analytic.browse(pool["dims"].get(dim, {}).get("id"))
                for dim in _CORE_DIMS
            }
            account = self.env["budget.account"].browse(pool["account"]["id"])
            wiz.update(
                {
                    "pool_found": True,
                    "pool_account_id": account.id,
                    "pool_department_analytic_id": dims["department_analytic_id"].id,
                    "pool_source_analytic_id": dims["source_analytic_id"].id,
                    "pool_fund_analytic_id": dims["fund_analytic_id"].id,
                    "pool_activity_analytic_id": dims["activity_analytic_id"].id,
                    "pool_label": self._coordinate_label(account, dims.values()),
                    "floating_available": detail["available"],
                }
            )

    @api.depends("project_id")
    def _compute_project_info(self):
        for wiz in self:
            project = wiz.project_id.sudo()
            active = project.budget_commitment_ids.filtered(
                lambda c: c.state != "cancel"
            )[:1]
            if not active:
                status = "none"
            elif active.total_obligated or active.total_consumed:
                status = "spending"
            else:
                status = "reserved"
            wiz.update(
                {
                    "project_label": " ".join(
                        filter(None, [project.key, project.name])
                    ),
                    "project_coordinate": self._coordinate_label(
                        project.budget_account_id, [project[d] for d in _CORE_DIMS]
                    ),
                    "project_received": project.budget_amount,
                    "plan_total": project.budget_expense_total,
                    "commitment_status": status,
                }
            )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------
    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("จัดสรรงบประมาณ (งบลอย)"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _check_amount(self):
        if float_compare(self.amount, 0.0, precision_digits=2) <= 0:
            raise UserError(_("กรุณาระบุจำนวนเงินที่ต้องการจัดสรรมากกว่า 0"))
        if not self.pool_found:
            raise UserError(
                _("ไม่พบเงินลอยที่รหัสงบประมาณ/มิติของโครงการนี้ กรุณาทำใบโอนงบประมาณตามขั้นตอนปกติ")
            )
        if float_compare(self.amount, self.floating_available, precision_digits=2) > 0:
            raise UserError(
                _("จำนวนเงินเกินเงินลอยคงเหลือ (%s)")
                % "{:,.2f}".format(self.floating_available)
            )

    def action_next(self):
        self.ensure_one()
        self.project_id._check_floating_allocation_allowed()
        self._check_amount()
        self.step = "review"
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.step = "input"
        return self._reopen()

    def _prepare_transfer_vals(self):
        project = self.project_id.sudo()
        vals = {
            "date": fields.Date.context_today(self),
            "account_fiscal_year_id": project.account_fiscal_year_id.id,
            "department_analytic_id": project.department_analytic_id.id,
            "source_analytic_id": project.source_analytic_id.id,
            "reason": self.note
            or _("จัดสรรงบประมาณจากเงินลอยเข้าโครงการ %s")
            % " ".join(filter(None, [project.key, project.name])),
            "is_floating_allocation": True,
            "kmitl_project_id": project.id,
            "line_ids": [
                Command.create(
                    {
                        "transfer_direction": "from",
                        "account_id": self.pool_account_id.id,
                        "amount": self.amount,
                        "department_analytic_id": self.pool_department_analytic_id.id,
                        "activity_analytic_id": self.pool_activity_analytic_id.id,
                        "fund_analytic_id": self.pool_fund_analytic_id.id,
                    }
                ),
                Command.create(
                    {
                        "transfer_direction": "to",
                        "account_id": project.budget_account_id.id,
                        "amount": self.amount,
                        "department_analytic_id": project.department_analytic_id.id,
                        "activity_analytic_id": project.activity_analytic_id.id,
                        "fund_analytic_id": project.fund_analytic_id.id,
                        "kmitl_project_analytic_id": project.analytic_account_id.id,
                    }
                ),
            ],
        }
        if "operating_unit_id" in self.env["budget.transfer"]._fields:
            # Stamp the project's unit, not the acting user's default.
            vals["operating_unit_id"] = project.operating_unit_id.id
        return vals

    def action_confirm(self):
        """Create the transfer, run the ordinary ยืนยัน checks, post at once."""
        self.ensure_one()
        project = self.project_id
        project._check_floating_allocation_allowed()
        self._check_amount()
        pool_label = self.pool_label
        transfer = self.env["budget.transfer"].create(self._prepare_transfer_vals())
        transfer.action_submit()
        if transfer.state != "submitted":
            # The exception framework returned its review popup instead of
            # raising; surface its rules here (rolls the transfer back).
            names = (
                transfer.exception_ids.mapped("name")
                if "exception_ids" in transfer._fields
                else []
            )
            raise UserError("\n".join([_("ไม่สามารถจัดสรรงบประมาณได้:")] + names))
        transfer.sudo().write(
            {"approver_id": self.env.uid, "approval_date": fields.Datetime.now()}
        )
        transfer.sudo()._post_transfer()
        transfer.message_post(
            body=_("จัดสรรตรงจากงบลอยผ่านหน้าโครงการ (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)")
        )
        project.sudo().message_post(
            body=_("จัดสรรงบประมาณ (งบลอย) %(amount)s บาท — ใบโอน %(name)s")
            % {"amount": "{:,.2f}".format(self.amount), "name": transfer.name}
        )
        self.write(
            {
                "step": "done",
                "transfer_id": transfer.id,
                "posted_pool_label": pool_label,
            }
        )
        return self._reopen()

    def action_open_transfer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer",
            "res_id": self.transfer_id.id,
            "view_mode": "form",
            "target": "current",
        }

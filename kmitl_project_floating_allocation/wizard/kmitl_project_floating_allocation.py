import json
import re

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

# The rows the cards show, in this order; a row without a value is skipped.
_DIM_ROWS = (
    ("source_analytic_id", "แหล่งเงิน"),
    ("department_analytic_id", "ส่วนงาน"),
    ("fund_analytic_id", "กองทุน"),
    ("activity_analytic_id", "ด้าน/แผนงาน/กิจกรรม"),
    ("account_id", "รหัสงบประมาณ"),
    ("kmitl_project_analytic_id", "โครงการ/กิจกรรม"),
    ("procurement_plan_analytic_id", "แผนจัดซื้อจัดจ้าง"),
)
# display_name is "[code] parent / … / leaf" — strip the code prefix.
_CODE_PREFIX = re.compile(r"^\[[^\]]*\]\s*")


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
    posted_pool_dims = fields.Char(readonly=True)
    transfer_name = fields.Char(related="transfer_id.name")
    transfer_date = fields.Datetime(related="transfer_id.approval_date")
    transfer_user_id = fields.Many2one(related="transfer_id.approver_id")

    # --- the floating pool (FROM card) -------------------------------------
    pool_found = fields.Boolean(compute="_compute_pool")
    pool_account_id = fields.Many2one("budget.account", compute="_compute_pool")
    pool_distribution = fields.Json(compute="_compute_pool")
    pool_dims = fields.Char(compute="_compute_pool")
    floating_available = fields.Float(
        digits="Budget Precision", compute="_compute_pool"
    )

    # --- the project (TO card) ---------------------------------------------
    project_label = fields.Char(compute="_compute_project_info")
    project_dims = fields.Char(compute="_compute_project_info")
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
    def _dim_rows(values):
        """JSON rows for the widget: label, code and the complete name split into
        its ancestors and leaf, in ``_DIM_ROWS`` order."""
        rows = []
        for key, label in _DIM_ROWS:
            record = values.get(key)
            if not record:
                continue
            names = _CODE_PREFIX.sub("", record.display_name or "").split(" / ")
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "code": record.code or "",
                    "path": names[:-1],
                    "leaf": names[-1],
                }
            )
        return json.dumps(rows, ensure_ascii=False)

    def _project_dims(self, project):
        """``{line column: analytic}`` of the project's ``analytic_distribution``,
        mapped the way the budget engine maps it."""
        return (
            self.env["budget.controller"]
            .sudo()
            ._parse_dimensions(project.analytic_distribution)
        )

    def _project_floating_distribution(self, project):
        """The project's coordinate without its own project dimension — where its
        floating money waits."""
        distribution = dict(project.analytic_distribution or {})
        distribution.pop(str(project.analytic_account_id.id), None)
        return distribution

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
                        "pool_distribution": False,
                        "pool_dims": "[]",
                        "floating_available": 0.0,
                    }
                )
                continue
            dims = {
                column: Analytic.browse(info["id"])
                for column, info in pool["dims"].items()
            }
            account = self.env["budget.account"].browse(pool["account"]["id"])
            wiz.update(
                {
                    "pool_found": True,
                    "pool_account_id": account.id,
                    "pool_distribution": {str(acc.id): 100 for acc in dims.values()},
                    "pool_dims": self._dim_rows(dict(dims, account_id=account)),
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
                    "project_dims": self._dim_rows(
                        dict(
                            self._project_dims(project),
                            account_id=project.budget_account_id,
                        )
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
        if float_compare(self.floating_available, 0.0, precision_digits=2) <= 0:
            raise UserError(_("เงินลอยสำหรับโครงการนี้ถูกใช้หมดแล้ว"))
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
        # The header (budget.move) has no analytic_distribution of its own.
        dims = self._project_dims(project)
        Analytic = self.env["account.analytic.account"]
        vals = {
            "date": fields.Date.context_today(self),
            "account_fiscal_year_id": project.account_fiscal_year_id.id,
            "department_analytic_id": dims.get("department_analytic_id", Analytic).id,
            "source_analytic_id": dims.get("source_analytic_id", Analytic).id,
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
                        "analytic_distribution": self.pool_distribution,
                    }
                ),
                Command.create(
                    {
                        "transfer_direction": "to",
                        "account_id": project.budget_account_id.id,
                        "amount": self.amount,
                        "analytic_distribution": project.analytic_distribution,
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
        pool_dims = self.pool_dims
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
                "posted_pool_dims": pool_dims,
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

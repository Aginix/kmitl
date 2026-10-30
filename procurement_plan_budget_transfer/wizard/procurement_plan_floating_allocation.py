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
    ("procurement_plan_analytic_id", "แผนจัดซื้อจัดจ้าง"),
)
# display_name is "[code] parent / … / leaf" — strip the code prefix.
_CODE_PREFIX = re.compile(r"^\[[^\]]*\]\s*")


class ProcurementPlanFloatingAllocation(models.TransientModel):
    """จัดสรรงบประมาณ (งบลอย) of a procurement plan — a Direct Floating
    Allocation (procurement_plan ADR-0006, same semantics as kmitl_project
    ADR-0009, implemented separately).

    Three steps — ``input``, ``review``, ``done`` — rendered by the
    ``procurement_plan_floating_return`` widget. Confirming posts a
    ``budget.transfer`` FROM the floating pool covering the plan's coordinate
    TO the plan's own dimension at once, with no approval.
    """

    _name = "procurement.plan.floating.allocation"
    _description = "จัดสรรงบประมาณ (งบลอย)"

    plan_id = fields.Many2one("procurement.plan", required=True, readonly=True)
    currency_id = fields.Many2one(related="plan_id.currency_id")
    # Read by the widget: ``allocate`` (pool → plan) or ``return``.
    direction = fields.Char(default="allocate", readonly=True)
    step = fields.Selection(
        [("input", "กรอกจำนวนเงิน"), ("review", "ตรวจสอบ"), ("done", "สำเร็จ")],
        default="input",
        required=True,
    )
    amount = fields.Monetary(string="จำนวนเงิน", currency_field="currency_id")
    note = fields.Char(string="บันทึกช่วยจำ")
    transfer_id = fields.Many2one("budget.transfer", readonly=True)
    # Snapshot for the slip: the pool may no longer resolve after posting.
    posted_pool_dims = fields.Char(readonly=True)
    transfer_name = fields.Char(related="transfer_id.name")
    transfer_date = fields.Datetime(related="transfer_id.approval_date")
    transfer_user_id = fields.Many2one(related="transfer_id.approver_id")

    # --- the floating pool -------------------------------------------------
    pool_found = fields.Boolean(compute="_compute_pool")
    pool_account_id = fields.Many2one("budget.account", compute="_compute_pool")
    pool_distribution = fields.Json(compute="_compute_pool")
    pool_dims = fields.Char(compute="_compute_pool")
    floating_available = fields.Monetary(
        currency_field="currency_id", compute="_compute_pool"
    )

    # --- the plan ----------------------------------------------------------
    plan_label = fields.Char(compute="_compute_plan_info")
    plan_dims = fields.Char(compute="_compute_plan_info")
    plan_received = fields.Monetary(
        currency_field="currency_id", compute="_compute_plan_info"
    )
    plan_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_plan_info"
    )
    commitment_status = fields.Selection(
        [("none", "ยังไม่จองงบ"), ("reserved", "จองงบแล้ว"), ("spending", "เริ่มใช้จ่ายแล้ว")],
        compute="_compute_plan_info",
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

    def _dims_of(self, account, distribution):
        """``{row key: record}`` of a budget code + distribution, mapped the way
        the budget engine maps it."""
        dims = (
            self.env["budget.controller"].sudo()._parse_dimensions(distribution or {})
        )
        return dict(dims, account_id=account)

    def _plan_floating_distribution(self, plan):
        """The plan's coordinate without its own plan dimension — where its
        floating money waits."""
        distribution = dict(plan.analytic_distribution or {})
        distribution.pop(str(plan.analytic_account_id.id), None)
        return distribution

    @api.depends("plan_id")
    def _compute_pool(self):
        controller = self.env["budget.controller"].sudo()
        for wiz in self:
            plan = wiz.plan_id.sudo()
            detail = {"available": 0.0, "pool": None}
            if plan.budget_account_id and plan.account_fiscal_year_id:
                detail = controller.get_available_detail(
                    plan.budget_account_id,
                    self._plan_floating_distribution(plan),
                    plan.account_fiscal_year_id.id,
                    plan.company_id.id,
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
            account = self.env["budget.account"].sudo().browse(pool["account"]["id"])
            distribution = {str(d["id"]): 100 for d in pool["dims"].values()}
            wiz.update(
                {
                    "pool_found": True,
                    "pool_account_id": account.id,
                    "pool_distribution": distribution,
                    "pool_dims": self._dim_rows(self._dims_of(account, distribution)),
                    "floating_available": detail["available"],
                }
            )

    @api.depends("plan_id")
    def _compute_plan_info(self):
        for wiz in self:
            plan = wiz.plan_id.sudo()
            active = plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel")[
                :1
            ]
            if not active:
                status = "none"
            elif active.total_obligated or active.total_consumed:
                status = "spending"
            else:
                status = "reserved"
            wiz.update(
                {
                    "plan_label": " ".join(filter(None, [plan.name, plan.description])),
                    "plan_dims": self._dim_rows(
                        self._dims_of(
                            plan.budget_account_id, plan.analytic_distribution
                        )
                    ),
                    "plan_received": plan.budget_amount,
                    "plan_total": plan.total_price,
                    "commitment_status": status,
                }
            )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------
    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": self._description,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _check_allowed(self):
        self.plan_id._check_floating_allocation_allowed()

    def _check_amount(self):
        rounding = self.currency_id.rounding or 0.01
        if float_compare(self.amount, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(_("กรุณาระบุจำนวนเงินที่ต้องการจัดสรรมากกว่า 0"))
        if not self.pool_found:
            raise UserError(
                _("ไม่พบเงินลอยที่รหัสงบประมาณ/มิติของแผนนี้ กรุณาทำใบโอนงบประมาณตามขั้นตอนปกติ")
            )
        if (
            float_compare(
                self.amount, self.floating_available, precision_rounding=rounding
            )
            > 0
        ):
            raise UserError(
                _("จำนวนเงินเกินเงินลอยคงเหลือ (%s)")
                % "{:,.2f}".format(self.floating_available)
            )

    def action_next(self):
        self.ensure_one()
        self._check_allowed()
        self._check_amount()
        self.step = "review"
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.step = "input"
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

    def _transfer_lines(self):
        """``(from, to)`` as ``(account, distribution)``."""
        plan = self.plan_id.sudo()
        return (
            (self.pool_account_id, self.pool_distribution),
            (plan.budget_account_id, plan.analytic_distribution),
        )

    def _prepare_transfer_vals(self):
        plan = self.plan_id.sudo()
        (from_account, from_dist), (to_account, to_dist) = self._transfer_lines()
        vals = {
            "date": fields.Date.context_today(self),
            "account_fiscal_year_id": plan.account_fiscal_year_id.id,
            "department_analytic_id": plan.department_analytic_id.id,
            "source_analytic_id": plan.source_analytic_id.id,
            "reason": self.note
            or _("จัดสรรงบประมาณจากเงินลอยเข้าแผนจัดซื้อจัดจ้าง %s") % plan.name,
            "is_procurement_plan_floating_allocation": True,
            "procurement_plan_id": plan.id,
            "line_ids": [
                Command.create(
                    {
                        "transfer_direction": "from",
                        "account_id": from_account.id,
                        "amount": self.amount,
                        "analytic_distribution": from_dist,
                    }
                ),
                Command.create(
                    {
                        "transfer_direction": "to",
                        "account_id": to_account.id,
                        "amount": self.amount,
                        "analytic_distribution": to_dist,
                    }
                ),
            ],
        }
        if "operating_unit_id" in self.env["budget.transfer"]._fields and (
            "operating_unit_id" in plan._fields
        ):
            # Stamp the plan's unit, not the acting user's default.
            vals["operating_unit_id"] = plan.operating_unit_id.id
        return vals

    def _post_transfer_messages(self, transfer):
        transfer.message_post(
            body=_(
                "จัดสรรตรงจากงบลอยผ่านหน้าแผนจัดซื้อจัดจ้าง (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)"
            )
        )
        self.plan_id.sudo().message_post(
            body=_("จัดสรรงบประมาณ (งบลอย) %(amount)s บาท — ใบโอน %(name)s")
            % {"amount": "{:,.2f}".format(self.amount), "name": transfer.name}
        )

    def action_confirm(self):
        """Create the transfer, run the ordinary ยืนยัน checks, post at once."""
        self.ensure_one()
        self._check_allowed()
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
            title = (
                _("ไม่สามารถโอนคืนงบลอยได้:")
                if self.direction == "return"
                else _("ไม่สามารถจัดสรรงบประมาณได้:")
            )
            raise UserError("\n".join([title] + names))
        transfer.sudo().write(
            {"approver_id": self.env.uid, "approval_date": fields.Datetime.now()}
        )
        transfer.sudo()._post_transfer()
        self._post_transfer_messages(transfer)
        self.write(
            {"step": "done", "transfer_id": transfer.id, "posted_pool_dims": pool_dims}
        )
        return self._reopen()

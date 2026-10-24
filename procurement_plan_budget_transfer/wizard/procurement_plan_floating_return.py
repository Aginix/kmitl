from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class ProcurementPlanFloatingReturn(models.TransientModel):
    """โอนคืนงบลอย — a Floating Return (procurement_plan ADR-0005/0006).

    Builds a ``budget.transfer`` FROM the plan's coordinate (with its
    ``procurement_plan`` dimension) TO the Floating Budget pool covering the
    plan's รหัสงบ + four dimensions — or, with no pool left there, the plan's own
    coordinate without its dimension — and posts it at once, with no approval.
    Money reserved but not yet obligated is released from the plan's reservation
    in the same move (budget ADR-0017). Same semantics as KMITL Project's
    Floating Return, implemented separately (ADR-0006).
    """

    _name = "procurement.plan.floating.return"
    _description = "โอนคืนงบลอย (แผนจัดซื้อจัดจ้าง)"

    plan_id = fields.Many2one("procurement.plan", required=True, readonly=True)
    currency_id = fields.Many2one(related="plan_id.currency_id")
    amount = fields.Monetary(string="จำนวนเงินที่โอนคืน", currency_field="currency_id")
    note = fields.Char(string="บันทึกช่วยจำ")
    plan_received = fields.Monetary(
        string="งบที่ได้รับการจัดสรร",
        currency_field="currency_id",
        compute="_compute_returnable",
    )
    claimed_label = fields.Char(string="กันไว้สำหรับ", compute="_compute_returnable")
    claimed_amount = fields.Monetary(
        string="ยอดที่ต้องกันไว้",
        currency_field="currency_id",
        compute="_compute_returnable",
    )
    returnable = fields.Monetary(
        string="โอนคืนได้สูงสุด",
        currency_field="currency_id",
        compute="_compute_returnable",
    )
    pool_account_id = fields.Many2one(
        "budget.account", string="รหัสงบประมาณปลายทาง", compute="_compute_pool"
    )
    pool_distribution = fields.Json(compute="_compute_pool")
    pool_label = fields.Char(string="คืนเข้าเงินลอยที่", compute="_compute_pool")

    @api.depends("plan_id")
    def _compute_returnable(self):
        for wiz in self:
            plan = wiz.plan_id.sudo()
            label, claimed = max(plan._get_plan_claims(), key=lambda c: c[1])
            wiz.update(
                {
                    "plan_received": plan.budget_amount,
                    "claimed_label": label,
                    "claimed_amount": claimed,
                    "returnable": max(plan.budget_amount - claimed, 0.0),
                }
            )

    def _plan_floating_distribution(self, plan):
        """The plan's coordinate without its own plan dimension — where its
        floating money waits."""
        distribution = dict(plan.analytic_distribution or {})
        distribution.pop(str(plan.analytic_account_id.id), None)
        return distribution

    @api.depends("plan_id")
    def _compute_pool(self):
        controller = self.env["budget.controller"].sudo()
        Analytic = self.env["account.analytic.account"].sudo()
        for wiz in self:
            plan = wiz.plan_id.sudo()
            distribution = self._plan_floating_distribution(plan)
            account = plan.budget_account_id
            pool = None
            if account and plan.account_fiscal_year_id:
                pool = controller.get_available_detail(
                    account,
                    distribution,
                    plan.account_fiscal_year_id.id,
                    plan.company_id.id,
                )["pool"]
            if pool:
                # Back into the pool the money was allocated from, so the return
                # never opens a pool nested with it (budget ADR-0016).
                account = (
                    self.env["budget.account"].sudo().browse(pool["account"]["id"])
                )
                distribution = {str(d["id"]): 100 for d in pool["dims"].values()}
            dims = Analytic.browse([int(k) for k in distribution])
            wiz.update(
                {
                    "pool_account_id": account.id,
                    "pool_distribution": distribution,
                    "pool_label": " / ".join(
                        filter(
                            None, [account.display_name] + dims.mapped("display_name")
                        )
                    ),
                }
            )

    def _check_amount(self):
        rounding = self.currency_id.rounding or 0.01
        if float_compare(self.amount, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(_("กรุณาระบุจำนวนเงินที่ต้องการโอนคืนมากกว่า 0"))
        if float_compare(self.amount, self.returnable, precision_rounding=rounding) > 0:
            raise UserError(
                _(
                    "จำนวนเงินเกินยอดที่โอนคืนได้ (%(cap)s) — กันไว้สำหรับ%(label)s %(claimed)s บาท"
                )
                % {
                    "cap": "{:,.2f}".format(self.returnable),
                    "label": self.claimed_label,
                    "claimed": "{:,.2f}".format(self.claimed_amount),
                }
            )

    def _prepare_transfer_vals(self):
        plan = self.plan_id.sudo()
        vals = {
            "date": fields.Date.context_today(self),
            "account_fiscal_year_id": plan.account_fiscal_year_id.id,
            "department_analytic_id": plan.department_analytic_id.id,
            "source_analytic_id": plan.source_analytic_id.id,
            "reason": self.note or _("โอนคืนงบลอยจากแผนจัดซื้อจัดจ้าง %s") % plan.name,
            "is_procurement_plan_floating_return": True,
            "procurement_plan_id": plan.id,
            "line_ids": [
                Command.create(
                    {
                        "transfer_direction": "from",
                        "account_id": plan.budget_account_id.id,
                        "amount": self.amount,
                        "analytic_distribution": plan.analytic_distribution,
                    }
                ),
                Command.create(
                    {
                        "transfer_direction": "to",
                        "account_id": self.pool_account_id.id,
                        "amount": self.amount,
                        "analytic_distribution": self.pool_distribution,
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

    def action_confirm(self):
        """Create the transfer, run the ordinary ยืนยัน checks, post at once."""
        self.ensure_one()
        self.plan_id._check_floating_return_allowed()
        self._check_amount()
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
            raise UserError("\n".join([_("ไม่สามารถโอนคืนงบลอยได้:")] + names))
        transfer.sudo().write(
            {"approver_id": self.env.uid, "approval_date": fields.Datetime.now()}
        )
        transfer.sudo()._post_transfer()
        transfer.message_post(
            body=_("โอนคืนงบลอยผ่านหน้าแผนจัดซื้อจัดจ้าง (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)")
        )
        self.plan_id.sudo().message_post(
            body=_("โอนคืนงบลอย %(amount)s บาท — ใบโอน %(name)s")
            % {"amount": "{:,.2f}".format(self.amount), "name": transfer.name}
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer",
            "res_id": transfer.id,
            "view_mode": "form",
            "target": "current",
        }

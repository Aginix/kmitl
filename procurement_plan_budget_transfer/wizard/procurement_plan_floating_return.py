from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class ProcurementPlanFloatingReturn(models.TransientModel):
    """โอนคืนงบลอย — a Floating Return (procurement_plan ADR-0005/0006).

    The reverse of the allocation wizard it inherits: posts a ``budget.transfer``
    FROM the plan's coordinate (with its dimension) TO the floating pool covering
    it — or, with no pool left there, the plan's own coordinate without its
    dimension. Money reserved but not yet obligated is released from the plan's
    reservation in the same move (budget ADR-0017).
    """

    _name = "procurement.plan.floating.return"
    _inherit = "procurement.plan.floating.allocation"
    _description = "โอนคืนงบลอย"

    direction = fields.Char(default="return", readonly=True)
    claimed_label = fields.Char(compute="_compute_pool")
    claimed_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_pool"
    )

    @api.depends("plan_id")
    def _compute_pool(self):
        # Back into the pool the allocation draws from (budget ADR-0016); with
        # no pool left, the plan's own coordinate without its dimension. What
        # can leave: received minus the largest claim on it.
        super()._compute_pool()
        for wiz in self:
            plan = wiz.plan_id.sudo()
            if not (plan.analytic_account_id and plan.budget_account_id):
                wiz.update(
                    {
                        "pool_found": False,
                        "floating_available": 0.0,
                        "claimed_label": False,
                        "claimed_amount": 0.0,
                    }
                )
                continue
            if not wiz.pool_found:
                distribution = self._plan_floating_distribution(plan)
                wiz.update(
                    {
                        "pool_found": True,
                        "pool_account_id": plan.budget_account_id.id,
                        "pool_distribution": distribution,
                        "pool_dims": self._dim_rows(
                            self._dims_of(plan.budget_account_id, distribution)
                        ),
                    }
                )
            label, claimed = max(plan._get_plan_claims(), key=lambda c: c[1])
            wiz.update(
                {
                    "claimed_label": label,
                    "claimed_amount": claimed,
                    "floating_available": max(plan.budget_amount - claimed, 0.0),
                }
            )

    def _check_allowed(self):
        self.plan_id._check_floating_return_allowed()

    def _check_amount(self):
        rounding = self.currency_id.rounding or 0.01
        if float_compare(self.amount, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(_("กรุณาระบุจำนวนเงินที่ต้องการโอนคืนมากกว่า 0"))
        if (
            float_compare(
                self.amount, self.floating_available, precision_rounding=rounding
            )
            > 0
        ):
            raise UserError(
                _(
                    "จำนวนเงินเกินยอดที่โอนคืนได้ (%(cap)s) — กันไว้สำหรับ%(label)s %(claimed)s บาท"
                )
                % {
                    "cap": "{:,.2f}".format(self.floating_available),
                    "label": self.claimed_label,
                    "claimed": "{:,.2f}".format(self.claimed_amount),
                }
            )

    def _transfer_lines(self):
        from_line, to_line = super()._transfer_lines()
        return to_line, from_line

    def _prepare_transfer_vals(self):
        vals = super()._prepare_transfer_vals()
        vals.update(
            {
                "reason": self.note
                or _("โอนคืนงบลอยจากแผนจัดซื้อจัดจ้าง %s") % self.plan_id.sudo().name,
                "is_procurement_plan_floating_allocation": False,
                "is_procurement_plan_floating_return": True,
            }
        )
        return vals

    def _post_transfer_messages(self, transfer):
        transfer.message_post(
            body=_("โอนคืนงบลอยผ่านหน้าแผนจัดซื้อจัดจ้าง (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)")
        )
        self.plan_id.sudo().message_post(
            body=_("โอนคืนงบลอย %(amount)s บาท — ใบโอน %(name)s")
            % {"amount": "{:,.2f}".format(self.amount), "name": transfer.name}
        )

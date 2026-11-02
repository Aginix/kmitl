import logging

from odoo import _, api, fields, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    """Auto-จองงบ a procurement plan the instant a transfer fully funds it.

    งานแผน funds a plan by transferring budget INTO its ``procurement_plan``
    dimension (ปรับเข้าแผน); normally the plan is then reserved by hand
    (ยืนยัน → ``action_verify`` → ``_reserve_plan_commitment``). This bridge
    closes the loop: when a transfer is approved/posted and a plan it funded
    now has its allocated budget (``budget_amount``) covering its planned
    amount (``total_price``), the plan is verified — and therefore reserved for
    what it received — automatically (procurement_plan ADR-0003).
    """

    _inherit = "budget.transfer"

    # Mark the transfers a Direct Floating Allocation / Floating Return creates
    # from a plan — they post on confirm, without approval, so stay auditable.
    is_procurement_plan_floating_allocation = fields.Boolean(
        string="จัดสรรตรงจากงบลอยเข้าแผน",
        readonly=True,
        copy=False,
        help="โอนจากเงินลอยเข้ามิติแผนจัดซื้อจัดจ้างโดยตรง (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)",
    )
    is_procurement_plan_floating_return = fields.Boolean(
        string="โอนคืนงบลอยจากแผน",
        readonly=True,
        copy=False,
        help="โอนเงินจากมิติแผนจัดซื้อจัดจ้างคืนเป็นเงินลอย (ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)",
    )
    procurement_plan_id = fields.Many2one(
        "procurement.plan",
        string="แผนจัดซื้อจัดจ้าง",
        readonly=True,
        copy=False,
        index=True,
    )

    procurement_plan_line_ids = fields.Many2many(
        "budget.move.line",
        string="แผนจัดซื้อจัดจ้าง",
        compute="_compute_procurement_plan_line_ids",
        help="FROM/TO lines that carry a procurement-plan dimension.",
    )

    @api.depends(
        "from_line_ids.procurement_plan_analytic_id",
        "to_line_ids.procurement_plan_analytic_id",
    )
    def _compute_procurement_plan_line_ids(self):
        for transfer in self:
            transfer.procurement_plan_line_ids = (
                transfer.from_line_ids | transfer.to_line_ids
            ).filtered("procurement_plan_analytic_id")

    def _skip_submit_review(self):
        return (
            self.is_procurement_plan_floating_allocation
            or self.is_procurement_plan_floating_return
            or super()._skip_submit_review()
        )

    def _post_transfer(self):
        # Reserve only after super() has posted the delegated move and moved the
        # transfer to ``posted`` — the just-posted lines must be in the ledger
        # before the plan's allocated amount is recomputed against them.
        res = super()._post_transfer()
        self._auto_reserve_funded_procurement_plans()
        return res

    def _auto_reserve_funded_procurement_plans(self):
        # System side-effect of an already-authorised approval: run through sudo
        # so a transfer approver without procurement.plan / budget.commitment
        # write rights can still trigger it, and so an appropriation in another
        # operating unit isn't hidden by record rules while checking funding.
        # sudo() keeps the acting user (the reservation stays attributed to
        # them; its OU is stamped from the plan, not the user).
        Plan = self.env["procurement.plan"].sudo()
        for transfer in self:
            tags = transfer.line_ids.filtered(
                lambda line: (
                    line.transfer_direction == "to"
                    and line.account_is_procurement
                    and line.procurement_plan_analytic_id
                )
            ).mapped("procurement_plan_analytic_id")
            if not tags:
                continue
            plans = Plan.search(
                [
                    ("analytic_account_id", "in", tags.ids),
                    ("state", "=", "to_verify"),
                ]
            )
            if not plans:
                continue
            # The transfer's move lines were just posted in this transaction;
            # drop any cached allocated amount so it recomputes against them.
            plans.invalidate_recordset(["budget_amount"])
            for plan in plans:
                if plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
                    continue  # already reserved
                rounding = plan.currency_id.rounding or 0.01
                fully_funded = (
                    float_compare(plan.total_price, 0.0, precision_rounding=rounding)
                    > 0
                    and float_compare(
                        plan.budget_amount,
                        plan.total_price,
                        precision_rounding=rounding,
                    )
                    >= 0
                )
                if not fully_funded:
                    continue
                try:
                    plan.action_verify()  # → _on_verify → _reserve_plan_commitment
                except Exception as err:  # never let a reserve hiccup void the post
                    _logger.warning(
                        "Auto-reserve of procurement plan %s after transfer %s "
                        "failed: %s",
                        plan.display_name,
                        transfer.name,
                        err,
                    )
                    transfer.message_post(
                        body=_(
                            "ไม่สามารถจองงบประมาณอัตโนมัติสำหรับแผนจัดซื้อจัดจ้าง "
                            "%(plan)s ได้ (%(err)s) กรุณาจองงบด้วยตนเอง"
                        )
                        % {"plan": plan.display_name, "err": err}
                    )

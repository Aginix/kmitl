from odoo import _, fields, models
from odoo.exceptions import UserError


class BudgetCommitmentReturnWizard(models.TransientModel):
    """Confirmation wizard to return leftover reserved budget (ส่งคืนเงินเหลือจ่าย).

    Read-only confirmation: it shows the computed return amount (the unconsumed
    remainder of the reservation), the budget code and analytic dimensions, then
    posts a single negative ``reserve`` line (``is_return=True``) to release the
    earmark back to the pool. The commitment is not cancelled; it auto-closes to
    ``done`` once the leftover is returned. See ``budget/CONTEXT.md``
    (Return Unused Reservation / คืนจอง) and ADR-0009.
    """

    _name = "budget.commitment.return.wizard"
    _description = "Return Leftover Reserved Budget"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        readonly=True,
    )
    # Full picture shown alongside the return amount: จองทั้งหมด − เบิกจ่ายแล้ว = ส่งคืน.
    total_reserved = fields.Monetary(
        related="commitment_id.total_reserved",
        string="ยอดจองทั้งหมด",
        currency_field="currency_id",
    )
    total_consumed = fields.Monetary(
        related="commitment_id.total_consumed",
        string="เบิกจ่ายแล้ว",
        currency_field="currency_id",
    )
    return_amount = fields.Monetary(
        related="commitment_id.available_to_obligate",
        string="ยอดส่งคืน",
        currency_field="currency_id",
        help="ยอดเงินจองที่ยังไม่ได้ตัด ซึ่งจะถูกส่งคืนเข้ากระเป๋างบประมาณ",
    )
    name = fields.Char(
        string="รายละเอียด",
        default=lambda self: _("ส่งคืนเงินเหลือจ่าย"),
    )
    date = fields.Date(
        string="วันที่",
        default=fields.Date.context_today,
        required=True,
    )

    # Display fields from the header (readonly) — echo the line that gets posted.
    account_id = fields.Many2one(
        related="commitment_id.account_id", string="รหัสงบประมาณ"
    )
    department_analytic_id = fields.Many2one(
        related="commitment_id.department_analytic_id", string="ส่วนงาน"
    )
    source_analytic_id = fields.Many2one(
        related="commitment_id.source_analytic_id", string="แหล่งเงิน"
    )
    activity_analytic_id = fields.Many2one(
        related="commitment_id.activity_analytic_id", string="กิจกรรม"
    )
    fund_analytic_id = fields.Many2one(
        related="commitment_id.fund_analytic_id", string="กองทุน"
    )
    currency_id = fields.Many2one(related="commitment_id.currency_id")

    def action_confirm(self):
        """Post the negative reserve line (คืนจอง) for the leftover remainder.

        The amount is re-read from the commitment at confirm time (not the cached
        display value) so a concurrent consume cannot let us over-return. The
        account and dimensions are taken from the first posted reserve line — the
        same convention the disbursement consume flow uses — so the reversal nets
        at the original control node. A single aggregate line is the only
        well-defined return because consume never splits per budget code (ADR-0009).
        """
        self.ensure_one()
        commitment = self.commitment_id
        amount = commitment.available_to_obligate
        if amount <= 0:
            raise UserError(_("No leftover reserved budget to return."))
        reserve_line = commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve"
            and l.state == "posted"
            and not l.is_return
        )[:1]
        if not reserve_line:
            raise UserError(_("No active reserve line to return against."))
        vals = {
            "commitment_id": commitment.id,
            "move_type": "reserve",
            "is_return": True,
            "account_id": reserve_line.account_id.id,
            "analytic_distribution": reserve_line.analytic_distribution,
            "amount": -amount,
            "name": self.name or _("ส่งคืนเงินเหลือจ่าย"),
            "date": self.date,
        }
        # Carry the source document through from the opener (e.g. a DR), mirroring
        # the consume flow's res_model/res_id stamping for drill-down traceability.
        ctx = self.env.context
        if ctx.get("default_res_model"):
            vals["res_model"] = ctx["default_res_model"]
        if ctx.get("default_res_id"):
            vals["res_id"] = ctx["default_res_id"]
        # Returning the leftover drives the commitment to ``done`` but must NOT
        # auto-close the owning procurement plan (ADR-0009); the flag is read by
        # procurement_plan's _sync_state override.
        self.env["budget.commitment.line"].with_context(
            skip_plan_autoclose=True
        ).create(vals)
        return {"type": "ir.actions.act_window_close"}

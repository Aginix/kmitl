import logging

from odoo.tools.misc import format_amount
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    # This layer gives ``to_verify`` its budget meaning — the plan waits here for
    # งานแผน to allocate budget (ปรับเข้าแผน) and then reserves it (จองงบ) — so
    # relabel the state to match. ``selection_add`` on an existing key overrides
    # its label only (no new value, no ondelete needed).
    state = fields.Selection(
        selection_add=[
            ("to_verify", "รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ"),
        ],
    )

    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        tracking=True,
        domain="[('procurement_plan', '=', True), ('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        states={
            "to_verify": [("readonly", True)],
            "in_progress": [("readonly", True)],
            "done": [("readonly", True)],
            "cancel": [("readonly", True)],
        },
    )

    budget_commitment_ids = fields.One2many(
        "budget.commitment",
        "procurement_plan_id",
        string="ผูกพันงบประมาณ",
        readonly=True,
        # Duplicating a plan copies its dimensions (มิติบัญชี) but must start with
        # a clean reservation — the ใบจอง belongs to the original plan only.
        copy=False,
    )
    budget_commitment_count = fields.Integer(
        string="จำนวนผูกพันงบประมาณ", compute="_compute_budget_commitment_count"
    )

    budget_amount = fields.Float(
        string="งบประมาณที่ได้รับการจัดสรร",
        digits="Product Price",
        compute="_compute_budget_amount",
        help="งบประมาณที่ได้รับจัดสรรจริง คำนวณจากยอดโอนเข้า-ออก (budget.move.line) "
        "ที่ตรงกับรหัสงบและมิติทั้งหมดของแผน (รวมมิติแผนจัดซื้อจัดจ้าง)",
    )

    budget_move_line_count = fields.Integer(
        string="รายการเคลื่อนไหวงบ",
        compute="_compute_budget_move_line_count",
    )

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    @api.depends(
        "analytic_account_id",
        "analytic_distribution",
        "budget_account_id",
        "account_fiscal_year_id",
        "company_id",
    )
    def _compute_budget_amount(self):
        """Current Budget at the plan's **full target coordinate**: Σ posted
        appropriation/entry balance on budget.move.line matching the plan's
        รหัสงบ (``budget_account_id``) + every budget dimension (the four base
        dims + the plan's own ``procurement_plan`` dim). Scopes to the same
        coordinate as the reserve availability check. Reads 0 before งานแผน
        transfers budget in (ปรับเข้าแผน), which is what gates จองงบ."""
        BML = self.env["budget.move.line"]
        _APPROPRIATION_TYPES = ("appropriation", "entry")
        for rec in self:
            if (
                not rec.analytic_account_id
                or not rec.account_fiscal_year_id
                or not rec.budget_account_id
            ):
                rec.budget_amount = 0.0
                continue
            domain = [
                ("parent_state", "=", "posted"),
                ("move_type", "in", list(_APPROPRIATION_TYPES)),
                ("account_fiscal_year_id", "=", rec.account_fiscal_year_id.id),
                ("company_id", "=", rec.company_id.id),
                ("account_id", "=", rec.budget_account_id.id),
                ("procurement_plan_analytic_id", "=", rec.analytic_account_id.id),
                ("department_analytic_id", "=", rec.department_analytic_id.id),
                ("fund_analytic_id", "=", rec.fund_analytic_id.id),
                ("source_analytic_id", "=", rec.source_analytic_id.id),
                ("activity_analytic_id", "=", rec.activity_analytic_id.id),
            ]
            groups = BML.read_group(domain, ["balance"], [])
            rec.budget_amount = (groups[0].get("balance") or 0.0) if groups else 0.0

    def _compute_budget_move_line_count(self):
        BML = self.env["budget.move.line"]
        for rec in self:
            if not rec.analytic_account_id:
                rec.budget_move_line_count = 0
                continue
            rec.budget_move_line_count = BML.search_count(
                [
                    ("procurement_plan_analytic_id", "=", rec.analytic_account_id.id),
                    ("account_fiscal_year_id", "=", rec.account_fiscal_year_id.id),
                ]
            )

    def action_open_budget_move_lines(self):
        self.ensure_one()
        return {
            "name": _("รายการเคลื่อนไหวงบประมาณ"),
            "type": "ir.actions.act_window",
            "res_model": "budget.move.line",
            "view_mode": "tree,form",
            "domain": ['&',
                ("procurement_plan_analytic_id", "=", self.analytic_account_id.id),
                ("procurement_plan_analytic_id", "!=", False),
                ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
            ],
        }

    def action_view_budget_commitment(self):
        self.ensure_one()
        action = (
            self.env.ref(
                "procurement_plan_budget.action_budget_commitment_procurement_plan"
            )
            .sudo()
            .read()[0]
        )
        action["domain"] = [("procurement_plan_id", "=", self.id)]
        action["context"] = {"default_procurement_plan_id": self.id}
        return action

    def action_open_budget_commitments(self):
        self.ensure_one()
        return {
            "name": "Budget Commitments",
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment",
            "view_mode": "tree,form",
            "domain": [("procurement_plan_id", "=", self.id)],
        }

    def _on_verify(self):
        self._reserve_plan_commitment()

    def _on_reset(self):
        self._release_plan_commitment()

    def _on_cancel(self):
        self._release_plan_commitment()

    def _reserve_plan_commitment(self):
        """Reserve one shared budget.commitment for the plan when it is
        verified (จองงบ). Idempotent: skips when an active (non-cancelled)
        commitment already exists. Blocks on insufficient budget unless
        budget.allow_negative is set. Downstream PR/PO/DR draw this single
        commitment down."""
        self.ensure_one()
        if self.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
            return
        if not self.budget_account_id:
            raise UserError(_("กรุณาระบุรหัสงบประมาณก่อนจองงบประมาณ"))
        if self.total_price <= 0:
            raise UserError(_("กรุณาระบุวงเงินรวมให้มากกว่า 0 ก่อนจองงบประมาณ"))
        if self.budget_amount <= 0:
            raise UserError(
                _(
                    "ยังไม่ได้รับการจัดสรรงบประมาณ กรุณารอให้งานแผนโอนงบเข้าแผน "
                    "(ปรับเข้าแผน) ก่อนจึงจะจองงบประมาณได้"
                )
            )
        analytic_data = {
            "account_id": self.budget_account_id.id,
            "activity_analytic_id": self.activity_analytic_id.id or False,
            "department_analytic_id": self.department_analytic_id.id or False,
            "fund_analytic_id": self.fund_analytic_id.id or False,
            "source_analytic_id": self.source_analytic_id.id or False,
            # The source appropriation is tagged with this plan's own
            # procurement_plan dimension; the check must carry it too, otherwise
            # the engine pins procurement_plan empty and excludes the very
            # appropriation being drawn from (→ false "insufficient budget").
            "procurement_plan_analytic_id": self.analytic_account_id.id or False,
        }
        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )
        if not allow_negative:
            self.env["budget.controller"].check_budget_availability(
                analytic_data,
                self.total_price,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        commitment = self.env["budget.commitment"].create(
            self._prepare_plan_commitment_vals()
        )
        commitment.action_reserve()
        self.message_post(
            body=_("จองงบประมาณ %s จำนวน %s")
            % (
                commitment.name,
                format_amount(self.env, self.total_price, self.currency_id),
            )
        )

    def _prepare_plan_commitment_vals(self):
        """Build the create vals for the plan's shared reservation commitment.
        Split out of ``_reserve_plan_commitment`` so bridge modules can enrich the
        commitment — e.g. stamp the plan's operating unit so the reservation lands
        in the same OU as the plan/appropriation — without re-implementing the
        whole reservation flow."""
        self.ensure_one()
        dist = dict(self.analytic_distribution or {})
        return {
            "account_id": self.budget_account_id.id,
            "amount": self.total_price,
            "analytic_distribution": dist or False,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "company_id": self.company_id.id,
            "date": fields.Date.context_today(self),
            "ref": self.name,
            # ชื่อรายการของแผน = ชื่อใบจอง (budget.commitment._rec_name shows it
            # next to the number, so a drawing document can tell reservations apart).
            "title": "[%s] %s" % (self.name, self.description) if self.name else self.description,
            "description": self.description,
            "procurement_plan_id": self.id,
            "user_id": self.env.user.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "move_type": "reserve",
                        "account_id": self.budget_account_id.id,
                        "analytic_distribution": dist or False,
                        "amount": self.total_price,
                        "name": _("Initial reservation"),
                    },
                )
            ],
        }

    def _release_plan_commitment(self):
        """Release the plan's reservation when it leaves the active band
        (reset to draft / cancel). Cancels the commitment only while it is still
        untouched AND usage has not started; once the plan is in progress (a
        downstream document has linked the reservation) or any obligate/consume
        draw-down exists, the commitment is kept and a note is posted so in-flight
        spending is never stranded."""
        for plan in self:
            in_use = plan.state == "in_progress"
            for commitment in plan.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            ):
                if (
                    in_use
                    or commitment.total_obligated
                    or commitment.total_consumed
                ):
                    plan.message_post(
                        body=_(
                            "งบประมาณที่จองไว้ (%s) มีการใช้งานแล้ว "
                            "จึงไม่ยกเลิกการจอง"
                        )
                        % commitment.name
                    )
                    continue
                commitment.action_cancel()
                plan.message_post(
                    body=_("ยกเลิกการจองงบประมาณ %s") % commitment.name
                )

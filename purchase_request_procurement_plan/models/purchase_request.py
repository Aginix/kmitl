import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    use_procurement_plan = fields.Boolean(
        string="Use Procurement Plan",
        store=True,
        copy=False,
    )

    budget_selection_mode = fields.Selection(
        selection_add=[("procurement_plan", "แผนจัดซื้อจัดจ้าง")],
        ondelete={"procurement_plan": "set default"},
    )

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        string="แผนจัดซื้อจัดจ้าง",
        domain="",
        tracking=True,
        # 1 แผน = 1 พ.1: a copy would claim the plan a second time.
        copy=False,
    )
    procurement_plan_domain = fields.Binary(
        compute="_compute_procurement_plan_domain",
        help=(
            "Record-aware domain for the แผนจัดซื้อจัดจ้าง dropdown: it must leave "
            "out plans another live พ.1 already holds, which a static domain "
            "cannot express."
        ),
    )

    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "procurement_plan": "procurement_plan_analytic_id",
    }

    def _domain_budget_account_id(self):
        return super()._domain_budget_account_id() + [("procurement_plan", "=", False)]

    @api.depends("procurement_plan_id", "account_fiscal_year_id")
    def _compute_procurement_plan_domain(self):
        """Plans this request may be bought under (root ADR-0011): verified
        (money reserved), in the request's own fiscal year, on a purchasable,
        product-backed code, and not claimed by another live พ.1 — the plan is
        claimed the moment it is chosen.
        Claims are read with sudo: PR record rules hide other requesters' พ.1.
        OU scoping comes from the global procurement.plan rule."""
        # Only verified plans are offered, so only their claims matter.
        claims = (
            self.env["purchase.request"]
            .sudo()
            .search_read(
                [
                    ("procurement_plan_id.state", "=", "verified"),
                    ("state", "not in", ("rejected", "cancelled")),
                ],
                ["procurement_plan_id"],
            )
        )
        for rec in self:
            taken = [
                c["procurement_plan_id"][0] for c in claims if c["id"] != rec._origin.id
            ]
            rec.procurement_plan_domain = [
                ("state", "=", "verified"),
                ("account_fiscal_year_id", "=", rec.account_fiscal_year_id.id),
                ("id", "not in", taken),
                ("budget_account_id.purchase_ok", "=", True),
                ("budget_account_id.product_id", "!=", False),
            ]

    def copy(self, default=None):
        # The copy is not under the plan (1 แผน = 1 พ.1), so it must not keep the
        # plan's code and dims either, or Reserve would reserve anew on them.
        default = dict(default or {})
        if self.use_procurement_plan:
            default.setdefault("budget_account_id", False)
            default.setdefault("analytic_distribution", False)
        new = super().copy(default)
        if self.use_procurement_plan:
            new.line_ids.write({"analytic_distribution": False})
        return new

    def _procurement_under_fields(self):
        return super()._procurement_under_fields() | {"procurement_plan_id"}

    def _prepare_procurement_under_vals(self):
        """A chosen plan is claimed (1 แผน = 1 พ.1) and brings its budget code,
        fiscal year, full analytic distribution and procurement method — root
        ADR-0011. Choosing another answer releases it."""
        vals = super()._prepare_procurement_under_vals()
        plan = self.procurement_plan_id
        if plan and self.budget_selection_mode in ("normal", "procurement_plan"):
            self._check_one_active_pr(plan)
            vals.update(
                {
                    "budget_selection_mode": "procurement_plan",
                    "use_procurement_plan": True,
                    "budget_account_id": plan.budget_account_id.id,
                    "account_fiscal_year_id": plan.account_fiscal_year_id.id,
                    "analytic_distribution": plan.analytic_distribution or False,
                }
            )
            if plan.procurement_method_id:
                vals["procurement_method_id"] = plan.procurement_method_id.id
        elif plan:
            vals.update({"procurement_plan_id": False, "use_procurement_plan": False})
        elif self.use_procurement_plan:
            vals["use_procurement_plan"] = False
        return vals

    @api.onchange("budget_selection_mode")
    def _onchange_budget_selection_mode_procurement_plan(self):
        if self.budget_selection_mode != "procurement_plan":
            self.procurement_plan_id = False

    def _check_drawable_commitment(self, commitment):
        # A plan's shared commitment sits on a ``procurement_plan`` budget code
        # this PR may not *reserve new* on (ADR-0006), so the base gate — which
        # mirrors the full reserve-new field domain — would reject it. Drawing it
        # down is allowed, but the code must still be a purchasable, product-backed
        # PR budget code just like a directly selected one: check it against the
        # base domain (purchase_ok + product), lifting only the ``procurement_plan``
        # exclusion.
        if commitment.procurement_plan_id:
            if not self.env["budget.account"].search_count(
                super()._domain_budget_account_id()
                + [("id", "=", commitment.account_id.id)]
            ):
                raise UserError(_("รหัสงบประมาณของใบจองที่เลือกไม่สามารถใช้กับเอกสารนี้ได้"))
            return True
        return super()._check_drawable_commitment(commitment)

    def _inverse_procurement_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("procurement_plan")

    @api.depends("state", "use_procurement_plan", "procurement_plan_id")
    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        for rec in self:
            # A plan พ.1's code and dims are the plan's, in every state:
            # correcting them means changing the plan (root ADR-0011).
            if rec.use_procurement_plan:
                rec.is_budget_editable = False

    @api.onchange("procurement_plan_id")
    def _onchange_procurement_plan_id(self):
        """Preview the plan's code and method on the live form; the dimensions
        are written server-side (see _sync_procurement_under) — re-assigning
        analytic_distribution here would wipe it."""
        plan = self.procurement_plan_id
        if plan:
            if plan.procurement_method_id:
                self.procurement_method_id = plan.procurement_method_id.id
            self.budget_account_id = plan.budget_account_id.id
            if not self.title:
                self.title = plan.description

    @api.onchange("account_fiscal_year_id")
    def _onchange_account_fiscal_year_id_procurement_plan(self):
        # The year filters the plan dropdown: another year drops the pick.
        plan = self.procurement_plan_id
        if plan and plan.account_fiscal_year_id != self.account_fiscal_year_id:
            self.procurement_plan_id = False
            self.budget_account_id = False

    def action_view_procurement_plan(self):
        self.ensure_one()
        if not self.procurement_plan_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "view_mode": "form",
            "res_id": self.procurement_plan_id.id,
            "target": "current",
        }

    def _prepare_commitment_vals(
        self,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id,
        source_analytic_id,
        ref,
        description,
        budget_account_id,
        include_company=True,
        **kwargs,
    ):
        commitment_vals = super()._prepare_commitment_vals(
            amount,
            activity_analytic_id,
            fund_analytic_id,
            department_analytic_id,
            source_analytic_id,
            ref,
            description,
            budget_account_id,
            include_company=include_company,
            **kwargs,
        )

        if kwargs.get("procurement_plan_id"):
            commitment_vals["procurement_plan_id"] = kwargs["procurement_plan_id"]

        return commitment_vals

    def action_reserve_budget(self):
        """A plan พ.1 names the plan, not its ใบจอง (root ADR-0011): find the
        plan's single live commitment and draw it through the base draw-down
        path, which re-takes code/dims/FY from it. Reservation itself happened
        when the plan's appropriation posted."""
        self.ensure_one()
        plan = self.procurement_plan_id
        if plan:
            self._check_can_commit_budget()
            commitment = plan.sudo().budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
            if not commitment:
                raise UserError(
                    _("แผนจัดซื้อจัดจ้างยังไม่ได้จองงบประมาณ (แผนต้องอยู่สถานะรอดำเนินการ)")
                )
            self.reservation_commitment_id = commitment.id
        return super().action_reserve_budget()

    def _action_draw_from_reservation(self):
        """Draw a plan's shared commitment: enforce 1 แผน = 1 พ.1, link the plan,
        then run the base draw — which copies the commitment's dims/account/FY
        onto the PR + lines, validates via the already-overridden
        ``_check_drawable_commitment``, and advances state. The plan starts
        (``in_progress``) here, at Reserve, not when it is chosen (root
        ADR-0011). Also the backstop for a slip injected over RPC."""
        plan = self.reservation_commitment_id.procurement_plan_id
        if plan:
            # ``in_progress`` is accepted only for the plan's own holder: a
            # ตีกลับ/แก้ไข return re-reserves after the plan already started, and
            # พ.1 made by the old create-from-plan button started it at create.
            holder = self.budget_commitment_id.procurement_plan_id == plan
            if not (
                plan.state == "verified" or (plan.state == "in_progress" and holder)
            ):
                raise UserError(
                    _(
                        "แผนจัดซื้อจัดจ้าง %s ไม่อยู่สถานะรอดำเนินการ "
                        "จึงยังใช้ใบจองงบประมาณของแผนไม่ได้"
                    )
                    % plan.display_name
                )
            self._check_one_active_pr(plan)
            if self.procurement_plan_id != plan:
                self.write({"procurement_plan_id": plan.id})
            if plan.state == "verified":
                # The budget committer holds no write on procurement.plan.
                plan.sudo().action_in_progress()
        return super()._action_draw_from_reservation()

    def _release_commitment_on_draft(self):
        """ดึงกลับ (Reset) keeps a plan's shared commitment: the request is recalled
        to be edited, not to give up the plan's budget. The commitment is released
        only on ยกเลิก (Cancel) — see _cancel_budget_commitment."""
        self.ensure_one()
        if self.budget_commitment_id.procurement_plan_id:
            return False
        return super()._release_commitment_on_draft()

    def _cancel_budget_commitment(self):
        """Detach — never cancel — a shared plan commitment when a plan PR is
        cancelled or rejected: just release this PR's hold on it (D3). ดึงกลับ
        (Reset) keeps it (see _release_commitment_on_draft)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        if commitment and commitment.procurement_plan_id:
            self.write(
                {"budget_commitment_id": False, "reservation_commitment_id": False}
            )
            return True
        return super()._cancel_budget_commitment()

    def _check_one_active_pr(self, plan):
        """Raise unless this PR is the plan's only live PR (1 แผน ต่อ 1 ใบขอซื้อ).
        Checked when the plan is chosen — that is when it is claimed — and again
        at Reserve (root ADR-0011). sudo: PR record rules hide other requesters'
        พ.1, which would let a second claim through."""
        active_others = plan.sudo().purchase_request_ids.filtered(
            lambda r: r.id != self.id and r.state not in ("rejected", "cancelled")
        )
        if active_others:
            raise UserError(
                _("แผนจัดซื้อจัดจ้าง %s มีใบขอซื้อที่ยังดำเนินการอยู่แล้ว (1 แผน ต่อ 1 ใบขอซื้อ)")
                % plan.display_name
            )

    def button_rejected(self):
        res = super().button_rejected()
        for record in self:
            record._release_plan()
        return res

    def _action_do_cancel(self, reason):
        # Not button_cancel: that only opens the cancel wizard, and สารบรรณ
        # cancels through here directly.
        res = super()._action_do_cancel(reason)
        self._release_plan()
        return res

    def _release_plan(self):
        """A rejected or cancelled พ.1 gives its plan back: an undrawn plan was
        never started (its claim lapses with the พ.1's state), a drawn one returns
        from ``in_progress`` to ``verified`` so a replacement PR can be made — but
        only while nothing has been consumed and no other live PR holds it
        (ADR-0006, root ADR-0011)."""
        self.ensure_one()
        plan = self.procurement_plan_id.sudo()
        if not plan or plan.state != "in_progress":
            return
        active_others = plan.purchase_request_ids.filtered(
            lambda r: r.id != self.id and r.state not in ("rejected", "cancelled")
        )
        consumed = any(c.total_consumed for c in plan.budget_commitment_ids)
        if active_others or consumed:
            return
        plan.write({"state": "verified"})
        plan.message_post(
            body=_("ใบขอซื้อ %s ไม่ดำเนินการต่อ แผนกลับสู่สถานะรอดำเนินการ") % self.display_name
        )


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        required=False,
        tracking=True,
    )

    purchase_request_count = fields.Integer(
        string="Purchase Requests Count", compute="_compute_purchase_request_count"
    )

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        for record in self:
            record.purchase_request_count = len(record.purchase_request_ids)

    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="procurement_plan_id",
        string="Purchase Requests",
    )

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            "name": _("ใบขอซื้อ (พ.1)"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "domain": [("id", "in", self.purchase_request_ids.ids)],
        }
        # One plan normally holds a single PR — open it straight in form view.
        if len(self.purchase_request_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.purchase_request_ids.id})
        else:
            action["view_mode"] = "tree,form"
        return action

# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    use_project = fields.Boolean(
        string="Use KMITL Project",
        store=True,
    )

    budget_selection_mode = fields.Selection(
        selection_add=[("project", "โครงการ/กิจกรรม")],
        ondelete={"project": "set default"},
    )

    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        tracking=True,
    )

    project_analytic_id = fields.Many2one(
        "account.analytic.account",
        compute="_compute_project_analytic_id",
        inverse="_inverse_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        store=False,
        string="โครงการ/กิจกรรม (Analytic)",
    )

    @api.depends("analytic_distribution")
    def _compute_project_analytic_id(self):
        for rec in self:
            account_ids = [int(a) for a in rec.analytic_distribution or {}]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            rec.project_analytic_id = accounts.filtered(
                lambda a: a.plan_id.code == "kmitl_project"
            )[:1]

    def _inverse_project_analytic(self):
        for rec in self:
            dist = dict(rec.analytic_distribution or {})
            account_ids = [int(k) for k in dist.keys()]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            for acc in accounts.filtered(lambda a: a.plan_id.code == "kmitl_project"):
                dist.pop(str(acc.id), None)
            if rec.project_analytic_id:
                dist[str(rec.project_analytic_id.id)] = 100
            rec.analytic_distribution = dist or False

    def _domain_budget_account_id(self):
        # Standalone PRs must not draw directly on a project budget code — those
        # are reserved through projects (ADR-0007). Project-driven PRs prefill the
        # code (read-only), so the domain never blocks them.
        return super()._domain_budget_account_id() + [("is_project", "=", False)]

    def _reservation_commitment_mode_domain(self):
        # The project's approval gate rides in the picker itself, so an
        # ineligible slip is never offered (ADR-0010's precedent: the picker
        # excludes plan slips that already have an active PR). Needed because
        # the reservation is minted at the project's to_verify → to_send step —
        # a project still awaiting its signed หนังสือ therefore holds a live
        # commitment that must not be spendable yet (kmitl_project ADR-0005).
        domain = super()._reservation_commitment_mode_domain()
        if self.budget_selection_mode == "project":
            domain = domain + [
                ("account_id.is_project", "=", True),
                ("kmitl_project_id.state", "=", "in_progress"),
            ]
        return domain

    def _check_drawable_commitment(self, commitment):
        # A project's shared commitment sits on an ``is_project`` budget code this
        # PR may not *reserve new* on (ADR-0007), so the base gate — which mirrors
        # the full reserve-new field domain — would reject it. Drawing it down is
        # allowed, but the code must still be a purchasable, product-backed PR
        # budget code just like a directly selected one: check it against the base
        # domain (purchase_ok + product), lifting only the ``is_project`` exclusion.
        if commitment.kmitl_project_id:
            if not self.env["budget.account"].search_count(
                super()._domain_budget_account_id()
                + [("id", "=", commitment.account_id.id)]
            ):
                raise UserError(
                    _("รหัสงบประมาณของใบจองที่เลือกไม่สามารถใช้กับเอกสารนี้ได้")
                )
            return True
        return super()._check_drawable_commitment(commitment)

    @api.depends("state", "use_project", "kmitl_project_id")
    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        for rec in self:
            # Once a พ.1 is attributed to a project its budget is the project's,
            # in every state — ดึงกลับ recalls the request for editing, it does
            # not reopen the แหล่งงบประมาณ (ADR-0015). The PR-first draw is
            # unaffected: ``use_project`` is still False while the slip is being
            # picked, and is written only by the draw itself.
            if rec.use_project:
                rec.is_budget_editable = False

    # No _onchange to prefill from the project on purpose. A project-driven พ.1 is
    # only ever opened through action_create_purchase_request, which already passes
    # the whole budget context (fiscal year, budget account, analytic_distribution,
    # title) as context defaults — and _link_to_project re-writes it server-side on
    # create. analytic_distribution inherits the core analytic.mixin field whose
    # compute (_compute_analytic_distribution) is a no-op: re-assigning it inside the
    # new-record onchange cascade makes Odoo recompute it to False, wiping the
    # dimension fields on the unsaved form (they reappear only after save). Letting
    # default_get drive the prefill keeps the value stable and the dimensions visible.

    def action_view_kmitl_project(self):
        self.ensure_one()
        if not self.kmitl_project_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "view_mode": "form",
            "res_id": self.kmitl_project_id.id,
            "target": "current",
        }

    def _enforce_project_budget_cap(self, project):
        """Raise if this PR would push the project's total drawn amount over
        its reserved ``budget_amount`` (ADR-0007). Shared by the source-driven
        create-from-project flow and the PR-first draw-down path."""
        pr_total = project._project_pr_total()
        this_pr = sum(self.line_ids.mapped("estimated_cost"))
        if pr_total > project.budget_amount:
            raise UserError(
                _(
                    "ใบขอซื้อนี้ (%s) เกินงบประมาณคงเหลือของโครงการ "
                    "(คงเหลือ %s จากงบ %s)"
                )
                % (
                    "{:,.2f}".format(this_pr),
                    "{:,.2f}".format(project.budget_amount - (pr_total - this_pr)),
                    "{:,.2f}".format(project.budget_amount),
                )
            )

    def action_reserve_budget(self):
        """Project-driven PRs draw the project's shared commitment instead of
        creating their own. Many PRs may share one project commitment, capped at
        the project's reserved budget_amount (ADR-0007)."""
        self.ensure_one()
        # A picked ใบจองงบประมาณ (PR-first, incl. one changed after ดึงกลับ) takes
        # priority: fall through to the base draw so the *chosen* commitment is
        # drawn, not the project's default one.
        if (
            self.use_project
            and self.kmitl_project_id
            and not self.reservation_commitment_id
        ):
            project = self.kmitl_project_id
            commitment = project.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
            if not commitment:
                raise UserError(
                    _("โครงการยังไม่ได้จองงบประมาณ ไม่สามารถดำเนินการได้")
                )
            self._enforce_project_budget_cap(project)
            self.budget_commitment_id = commitment.id
            # Same rail as the reserve-new path: จองงบ advances to to_submit and
            # the ขออนุมัติ step is a separate press. (ADR-0006 described this as
            # to_verify → to_approve, but to_approve_allowed is keyed on
            # to_submit, so button_to_approve() here always raised.)
            self.button_to_submit()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }
        return super().action_reserve_budget()

    def _action_draw_from_reservation(self):
        """PR-first draw of a project's shared commitment (as opposed to the
        source-driven ``kmitl.project`` create-from-project button above):
        link the project, enforce its budget cap, then run the base draw —
        which copies the commitment's dims/account/FY onto the PR + lines,
        validates via the already-overridden ``_check_drawable_commitment``,
        and advances state. ``kmitl_project_id`` is written first so the cap
        check counts this PR and so ``_cancel_budget_commitment`` /
        ``is_budget_editable`` (both keyed on ``use_project``) behave."""
        project = self.reservation_commitment_id.kmitl_project_id
        if project:
            # Backstop for the picker domain: a พ.1 may only be raised from an
            # approved project, and the picker is not the only way in (context
            # default, RPC) — kmitl_project ADR-0005, budget ADR-0015.
            if project.state != "in_progress":
                raise UserError(
                    _(
                        "โครงการ %s ยังไม่ได้รับอนุมัติและกำลังดำเนินการ "
                        "จึงยังใช้ใบจองงบประมาณของโครงการไม่ได้"
                    )
                    % project.display_name
                )
            self.write({"use_project": True, "kmitl_project_id": project.id})
            self._enforce_project_budget_cap(project)
        return super()._action_draw_from_reservation()

    def _release_commitment_on_draft(self):
        """ดึงกลับ (Reset) keeps a project's shared commitment: the request is
        recalled to be edited, not to give up the project's budget. The commitment
        is released only on ยกเลิก (Cancel) — see _cancel_budget_commitment."""
        self.ensure_one()
        if self.budget_commitment_id.kmitl_project_id:
            return False
        return super()._release_commitment_on_draft()

    def _cancel_budget_commitment(self):
        """Detach — never cancel — a shared project commitment when a project PR is
        cancelled or rejected: just release this PR's hold on it (frees its
        headroom). ดึงกลับ (Reset) keeps it (see _release_commitment_on_draft)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        if commitment and commitment.kmitl_project_id:
            self.budget_commitment_id = False
            return True
        return super()._cancel_budget_commitment()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered(lambda r: r.kmitl_project_id):
            record._link_to_project()
        return records

    def _link_to_project(self):
        """A project-driven PR links the project's already-reserved shared
        commitment. Unlike a procurement plan, a project may hold many PRs against
        the one commitment (ADR-0007), so there is no one-active-PR constraint. The
        PR never advances the project's state: since kmitl_project ADR-0005 a
        project only reaches ``in_progress`` when its ขออนุมัติ หนังสือ is signed,
        and a พ.1 can only be raised from there.

        The project's budget context — budget account, fiscal year, the full
        analytic distribution (4 financial dimensions + the project's own
        kmitl_project dimension) and the shared commitment — is written here
        **server-side** so the พ.1 always carries it. The budget fields are locked
        and the dimension fields are computed from analytic_distribution, so the
        live-form context/onchange prefill alone is not a guarantee."""
        self.ensure_one()
        project = self.kmitl_project_id
        commitment = project.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]
        vals = {
            "use_project": True,
            "budget_account_id": project.budget_account_id.id,
            "account_fiscal_year_id": project.account_fiscal_year_id.id,
            "analytic_distribution": project.analytic_distribution or False,
        }
        if commitment:
            vals["budget_commitment_id"] = commitment.id
        self.write(vals)
        # write() does not fire the form's _onchange_analytic_distribution, so push
        # the project's distribution onto any existing lines explicitly.
        if self.line_ids and project.analytic_distribution:
            self.line_ids.write(
                {"analytic_distribution": project.analytic_distribution}
            )


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="kmitl_project_id",
        string="ใบขอซื้อ (พ.1)",
    )
    purchase_request_count = fields.Integer(
        compute="_compute_purchase_request_count"
    )

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        for record in self:
            record.purchase_request_count = len(record.purchase_request_ids)

    can_create_purchase_request = fields.Boolean(
        compute="_compute_can_create_purchase_request"
    )

    @api.depends(
        "state",
        "budget_amount",
        "budget_commitment_ids.state",
        "purchase_request_ids.state",
        "purchase_request_ids.line_ids.estimated_cost",
    )
    def _compute_can_create_purchase_request(self):
        """Show the create-PR button once the project is approved and executing
        (``in_progress`` with an active commitment — kmitl_project ADR-0005) and
        headroom remains under the reserved amount."""
        for rec in self:
            has_commitment = bool(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state in ("reserved", "partial")
                )
            )
            remaining = rec.budget_amount - rec._project_pr_total()
            rec.can_create_purchase_request = (
                rec.state == "in_progress" and has_commitment and remaining > 0
            )

    def _project_pr_total(self):
        """Total estimated cost already claimed by the project's non-rejected
        purchase requests."""
        self.ensure_one()
        return sum(
            sum(pr.line_ids.mapped("estimated_cost"))
            for pr in self.purchase_request_ids.filtered(
                lambda r: r.state != "rejected"
            )
        )

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            "name": _("ใบขอซื้อ (พ.1)"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "domain": [("id", "in", self.purchase_request_ids.ids)],
        }
        if len(self.purchase_request_ids) == 1:
            action.update(
                {"view_mode": "form", "res_id": self.purchase_request_ids.id}
            )
        else:
            action["view_mode"] = "tree,form"
        return action

    def action_create_purchase_request(self):
        """Create a purchase request (พ.1) from the project, pre-filled from the
        project's budget context (no procurement method — each PR picks its own).
        Many PRs may draw the project's single shared commitment, capped at
        budget_amount (ADR-0007)."""
        self.ensure_one()
        commitment = self.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]
        if self.state != "in_progress" or not commitment:
            raise UserError(
                _("สร้างใบขอซื้อได้เฉพาะโครงการที่ได้รับอนุมัติและกำลังดำเนินการเท่านั้น")
            )
        if self.budget_amount - self._project_pr_total() <= 0:
            raise UserError(
                _("งบประมาณของโครงการถูกจัดสรรให้ใบขอซื้อครบแล้ว")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("สร้างใบขอซื้อจากโครงการ"),
            "res_model": "purchase.request",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_use_project": True,
                "default_budget_selection_mode": "project",
                "default_kmitl_project_id": self.id,
                "default_budget_commitment_id": commitment.id,
                "default_budget_account_id": self.budget_account_id.id,
                "default_account_fiscal_year_id": self.account_fiscal_year_id.id,
                "default_analytic_distribution": self.analytic_distribution,
                "default_title": self.name,
            },
        }

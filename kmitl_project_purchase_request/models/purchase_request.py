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

    @api.depends("state", "use_project", "kmitl_project_id")
    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        for rec in self:
            if rec.use_project:
                rec.is_budget_editable = False

    @api.onchange("use_project", "kmitl_project_id")
    def _onchange_kmitl_project_id(self):
        if self.use_project and self.kmitl_project_id:
            self.account_fiscal_year_id = self.kmitl_project_id.account_fiscal_year_id.id
            self.budget_account_id = self.kmitl_project_id.budget_account_id.id
            self.analytic_distribution = self.kmitl_project_id.analytic_distribution
            self.title = self.kmitl_project_id.name

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

    def action_reserve_budget(self):
        """Project-driven PRs draw the project's shared commitment instead of
        creating their own. Many PRs may share one project commitment, capped at
        the project's reserved budget_amount (ADR-0007)."""
        self.ensure_one()
        if self.use_project and self.kmitl_project_id:
            project = self.kmitl_project_id
            commitment = project.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
            if not commitment:
                raise UserError(
                    _("โครงการยังไม่ได้จองงบประมาณ ไม่สามารถดำเนินการได้")
                )
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
            self.budget_commitment_id = commitment.id
            if project.state == "new":
                project.button_in_progress()
            self.button_to_approve()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }
        return super().action_reserve_budget()

    def _cancel_budget_commitment(self):
        """Never cancel a shared project commitment when a project-driven PR is
        reset or rejected — just detach this PR from it (frees its headroom)."""
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
        commitment and starts the project. Unlike a procurement plan, a project may
        hold many PRs against the one commitment (ADR-0007), so there is no
        one-active-PR constraint.

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
        if project.state == "new":
            project.button_in_progress()


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
        """Show the create-PR button once the project has reserved its budget
        (state new/in_progress with an active commitment) and headroom remains
        under the reserved amount."""
        for rec in self:
            has_commitment = bool(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state in ("reserved", "partial")
                )
            )
            remaining = rec.budget_amount - rec._project_pr_total()
            rec.can_create_purchase_request = (
                rec.state in ("new", "in_progress")
                and has_commitment
                and remaining > 0
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
        if self.state not in ("new", "in_progress") or not commitment:
            raise UserError(
                _("สร้างใบขอซื้อได้เฉพาะโครงการที่จองงบประมาณแล้วเท่านั้น")
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
                "default_kmitl_project_id": self.id,
                "default_budget_commitment_id": commitment.id,
                "default_budget_account_id": self.budget_account_id.id,
                "default_account_fiscal_year_id": self.account_fiscal_year_id.id,
                "default_analytic_distribution": self.analytic_distribution,
                "default_title": self.name,
            },
        }

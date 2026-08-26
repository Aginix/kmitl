# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools import float_compare


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # A disbursement belongs to a project through the ``kmitl_project`` dimension
    # carried in its ``analytic_distribution`` (a project is spent down by its own
    # purchase requests and disbursements — see kmitl_project CONTEXT.md). Mirror
    # that dimension into a stored column so the project can search/count its
    # disbursements exactly like it does its budget move lines. The JSON
    # distribution stays the source of truth; this is a read-only lookup.
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_analytic_id",
        store=True,
        domain=[("root_plan_id.code", "=", "kmitl_project")],
    )

    @api.depends("analytic_distribution")
    def _compute_kmitl_project_analytic_id(self):
        for rec in self:
            account_ids = [int(a) for a in rec.analytic_distribution or {}]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            rec.kmitl_project_analytic_id = accounts.filtered(
                lambda a: a.plan_id.code == "kmitl_project"
            )[:1]

    # Resolve the actual project record behind that dimension so the DR form can
    # link back to it with a smart button (its analytic account is unique per
    # project, minted once — see kmitl_project » Project Number).
    kmitl_project_id = fields.Many2one(
        "kmitl.project",
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_id",
        store=True,
    )

    @api.depends("kmitl_project_analytic_id")
    def _compute_kmitl_project_id(self):
        # sudo the lookup: kmitl.project read is gated to the project groups, but
        # every disbursement officer reads DRs. Resolving the link must not depend
        # on the reader holding project access (the DR already carries the dim).
        Project = self.env["kmitl.project"].sudo()
        for rec in self:
            rec.kmitl_project_id = (
                Project.search(
                    [("analytic_account_id", "=", rec.kmitl_project_analytic_id.id)],
                    limit=1,
                )
                if rec.kmitl_project_analytic_id
                else False
            )

    # True when this DR draws a project budget code.
    is_project_expense = fields.Boolean(
        related="budget_account_id.is_project",
        string="Is Project Expense",
    )

    # For project expenses the line product is not chosen by hand — it is the
    # product bound to the project budget account (budget_product). Hand both to
    # the disbursement hooks, which hide the product column and stamp the product
    # and its expense account on every line at ORM level. A code with no bound
    # product leaves the line blank and is refused on submit by the
    # excep_disbursement_project_no_product rule.
    @api.depends("budget_account_id.is_project")
    def _compute_is_budget_account_product_expense(self):
        super()._compute_is_budget_account_product_expense()
        for rec in self.filtered("is_project_expense"):
            rec.is_budget_account_product_expense = True

    def _budget_account_line_product(self):
        if self.is_project_expense:
            return self.budget_account_id.product_id
        return super()._budget_account_line_product()

    def _project_disbursement_claimed_total(self):
        """Total amount claimed by this project's non-cancelled disbursements
        (this DR included) — the disbursement analog of the พ.1 headroom cap that
        keeps a project's spend within its reserved Project Budget (ADR-0007).
        sudo: sibling DRs may belong to other requesters."""
        self.ensure_one()
        project = self.kmitl_project_id
        if not project:
            return 0.0
        siblings = self.env["disbursement.request"].sudo().search(
            [
                ("kmitl_project_id", "=", project.id),
                ("state", "!=", "cancel"),
            ]
        )
        return sum((siblings | self).mapped("amount_total"))

    def _exceeds_project_budget(self):
        """True when this project's disbursement claims overrun its Project Budget
        (the reserved ``budget_amount``). sudo the project read — budget_amount is
        gated to the project groups, but any requester may raise a DR."""
        self.ensure_one()
        project = self.kmitl_project_id.sudo()
        if not project:
            return False
        rounding = (self.currency_id or self.company_id.currency_id).rounding
        return (
            float_compare(
                self._project_disbursement_claimed_total(),
                project.budget_amount,
                precision_rounding=rounding,
            )
            > 0
        )

    def action_open_kmitl_project(self):
        self.ensure_one()
        if not self.kmitl_project_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "name": _("โครงการ/กิจกรรม"),
            "res_model": "kmitl.project",
            "res_id": self.kmitl_project_id.id,
            "view_mode": "form",
            "target": "current",
        }

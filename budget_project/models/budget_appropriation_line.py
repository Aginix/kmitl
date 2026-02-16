import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    is_project = fields.Boolean(
        related="account_id.is_project",
        store=True,
    )

    enable_project = fields.Boolean(default=False)

    project_type = fields.Selection(related="account_id.project_type", store=True)

    budget_project_id = fields.Many2one(
        comodel_name="budget.project",
        string="การกันเงินโครงการ",
    )

    @api.depends("enable_project")
    def _compute_highlight_row(self):
        super()._compute_highlight_row()
        for rec in self:
            if rec.enable_project:
                rec.highlight_row = True

    def _prepare_budget_project_vals(self):
        return {
            "name": self.description,
            "budget_amount": self.balance,
            "budget_account_id": self.account_id.id,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "analytic_distribution": self.analytic_distribution,
            "project_type": self.project_type,
            "user_id": self.appropriation_id.user_id.id,
            "company_id": self.appropriation_id.company_id.id,
        }

    def _create_budget_project(self):
        self.ensure_one()
        vals = self._prepare_budget_project_vals()
        budget_project = self.env["budget.project"].create(vals)
        self.budget_project_id = budget_project.id
        return budget_project

    def budget_move_line_vals(self):
        vals = super().budget_move_line_vals()
        if self.enable_project:
            budget_project = self._create_budget_project()
            vals["budget_project_id"] = budget_project.id
        return vals

    def _message_link_to_budget_project(self):
        budget_project = self.budget_project_id
        name = budget_project.name
        link = budget_project._get_record_url()
        return _(
            'การกันเงินโครงการ/กิจกรรมถูกสร้างจากการจัดสรรงบประมาณ: '
            '<a href="%(link)s" target="_blank">%(name)s</a>',
            link=link,
            name=name,
        )

    def _message_link_back_from_budget_project(self):
        appropriation_id = self.appropriation_id
        name = appropriation_id.name
        link = appropriation_id._get_record_url()
        return _(
            'สร้างจากการจัดสรรงบประมาณ: '
            '<a href="%(link)s" target="_blank">%(name)s</a>',
            link=link,
            name=name,
        )

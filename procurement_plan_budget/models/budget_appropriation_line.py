# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    procurement_plan = fields.Boolean(
        related="account_id.procurement_plan",
        store=False,
    )

    enable_procurement_plan = fields.Boolean("จัดสรรแผนจัดซื้อจัดจ้าง")
    procurement_plan_amount = fields.Integer(string="จำนวน")
    procurement_plan_unit = fields.Char("Unit of Measure")
    procurement_plan_id = fields.Many2one(comodel_name="procurement.plan")

    def _prepare_procurement_plan_vals(self):
        # The line's own analytic_distribution holds at most the line-level
        # dimensions; department/source live on the appropriation header (related
        # fields) and never sync into it. Build the full 4D distribution from the
        # convenience fields so the plan — and its reservation — carry every
        # dimension, not just activity/fund.
        distribution = dict(self.analytic_distribution or {})
        for dimension in (
            self.department_analytic_id,
            self.source_analytic_id,
            self.activity_analytic_id,
            self.fund_analytic_id,
        ):
            if dimension:
                distribution[str(dimension.id)] = 100
        return {
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "description": self.description,
            "amount": self.procurement_plan_amount,
            "unit": self.procurement_plan_unit,
            "total_price": self.balance,
            "user_id": self.appropriation_id.user_id.id,
            "budget_account_id": self.account_id.id,
            "analytic_distribution": distribution or False,
        }

    def _create_procurement_plan(self):
        self.ensure_one()
        vals = self._prepare_procurement_plan_vals()
        procurement_plan = self.env['procurement.plan'].create(vals)
        procurement_plan.action_new()

        self.procurement_plan_id = procurement_plan.id
        return procurement_plan

    def budget_move_line_vals(self):
        vals = super().budget_move_line_vals()

        if self.enable_procurement_plan:
            procurement_plan_id = self._create_procurement_plan()
            account_id = procurement_plan_id.analytic_account_id

            # analytic_distribution may be empty/False when the line carries no
            # dimensions; start from a fresh dict so item assignment never hits a
            # bool, and copy to avoid mutating the source field value.
            distribution = dict(vals.get('analytic_distribution') or {})
            distribution[str(account_id.id)] = 100
            vals['analytic_distribution'] = distribution
            vals['procurement_plan_id'] = procurement_plan_id.id
        return vals

    def _message_link_back_from_procurement_plan(self):
        appropriation_id = self.appropriation_id
        name = appropriation_id.name
        link = appropriation_id._get_record_url()

        return _(
            'This record has been created from: <a href="%(link)s" target="_blank">%(name)s</a>',
            link=link,
            name=name,
        )

    def _message_link_to_procurement_plan(self):
        procurement_plan_id = self.procurement_plan_id
        name = f"[{procurement_plan_id.name}] {procurement_plan_id.description}"
        link = procurement_plan_id._get_record_url()

        return _(
            'The procurement plan has been created from this budget appropriation: <a href="%(link)s" target="_blank">%(name)s</a>',
            link=link,
            name=name,
        )

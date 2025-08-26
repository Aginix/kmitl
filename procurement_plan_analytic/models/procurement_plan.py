# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _name = 'procurement.plan'
    _inherit = ['procurement.plan', "analytic.distribution.mixin"]

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        copy=False,
        ondelete="set null",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Analytic account to which this procurement plan. \n"
        "Track the costs and revenues of your procurement plan by setting this analytic account on your related documents (e.g. budgetings, purchase requests, purchase orders etc.).",
    )
    analytic_account_balance = fields.Monetary(related="analytic_account_id.balance")

    def unlink(self):
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env["account.analytic.account"]
        for record in self:
            if record.analytic_account_id and not record.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= record.analytic_account_id
        result = super().unlink()
        analytic_accounts_to_delete.unlink()
        return result

    def _create_analytic_account(self):
        plan_id = self.env.ref('procurement_plan_analytic.analytic_plan_procurement_plan', raise_if_not_found=True).id
        for record in self:
            analytic_account = self.env["account.analytic.account"].create(
                {
                    "name": record.name,
                    "company_id": record.company_id.id,
                    "plan_id": plan_id,
                    "active": True,
                }
            )
            record.write({"analytic_account_id": analytic_account.id})

    @api.model
    def _create_analytic_account_from_values(self, values):
        analytic_account = self.env['account.analytic.account'].create({
            'name': values.get('name', _('Unknown Analytic Account')),
            'company_id': self.env.company.id,
            'partner_id': values.get('partner_id'),
            'plan_id': self.env.ref('procurement_plan_analytic.analytic_plan_procurement_plan', raise_if_not_found=True).id,
        })
        return analytic_account

    def write(self, vals):
        if 'state' in vals and vals['state'] in ['pending', 'procurement', 'done'] and not self.analytic_account_id:
            analytic_account = self._create_analytic_account_from_values({
                "name": vals.get('name', self.name),
            })
            vals["analytic_account_id"] = analytic_account.id
        return super().write(vals)

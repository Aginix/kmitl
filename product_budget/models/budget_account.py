# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BudgetAccount(models.Model):
    _inherit = 'budget.account'

    product_count = fields.Integer(
        string="Products",
        compute="_compute_products_count",
        readonly=True
    )

    def _compute_products_count(self):
        for rec in self:
            rec.product_count = self.env['product.template'].search_count([('budget_account_id', '=', rec.id)])

    def action_view_products(self):
        self.ensure_one()
        return {
            'name': _('Products'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'product.template',
            'domain': [('budget_account_id', '=', self.id)],
            'context': {'default_budget_account_id': self.id},
        }

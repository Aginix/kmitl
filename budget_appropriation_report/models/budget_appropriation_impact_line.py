# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationImpactLine(models.Model):
    _name = 'budget.appropriation.impact.line'
    _description = 'BudgetAppropriationImpactLine'

    name = fields.Char('Name', related="analytic_account_id.name", readonly=True, store=True)
    report_id = fields.Many2one(
        comodel_name='budget.appropriation.report',
        string='รายงาน',
        ondelete='cascade',
        required=True,
    )
    impact_type = fields.Selection(
        selection=[
            ('education', 'ด้านการศึกษา (Education)'),
            ('academic', 'ด้านวการวิจัย (Academic)'),
            ('industrial', 'ด้านอุตสาหกรรม (Industrial)'),
            ('social', 'ด้านสังคม (Social)'),
        ],
        string='ประเภทผลกระทบ',
        required=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='กิจกรรม',
        domain=[('root_plan_id.code', '=', 'activities')],
        required=True,
    )
    amount = fields.Monetary(
        string='จำนวนเงิน',
        currency_field='currency_id',
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='สกุลเงิน',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='บริษัท',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.constrains('amount')
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('จำนวนเงินต้องเป็นค่าบวกเท่านั้น'))

    def action_delete(self):
        """Delete the record and return action to stay on the same view."""
        self.unlink()
        return {"type": "ir.actions.client", "tag": "soft_reload"}

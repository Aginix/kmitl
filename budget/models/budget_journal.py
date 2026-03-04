# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetJournal(models.Model):
    _name = "budget.journal"
    _description = "Budget Journal"
    _order = 'code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _rec_names_search = ['name', 'code']

    name = fields.Char(string="Journal Name", required=True)
    code = fields.Char(
        string="Short Code",
        size=5,
        required=True,
        help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.",
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Journal without removing it.",
    )
    default_budget_type = fields.Selection(
        [("revenue", "Revenue"), ("expense", "Expense")],
        string='Default Budget Type',
        required=False,
        copy=True,
        default="expense",
    )
    sequence = fields.Integer(help='Used to order Journals in the view', default=10)

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, index=True, default=lambda self: self.env.company,
        help="Company related to this journal")

    _sql_constraints = [
        ('code_company_uniq', 'unique (company_id, code)', 'Journal codes must be unique per company.'),
    ]

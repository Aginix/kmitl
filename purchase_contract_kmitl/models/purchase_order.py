# -*- coding: utf-8 -*-
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    READONLY_STATES = {
        "purchase": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    contract_type_id = fields.Many2one(
        "purchase.contract.type",
        string="Contract Type",
        states=READONLY_STATES,
        tracking=True
    )

    work_start = fields.Date(
        string="Work Start",
        states=READONLY_STATES,
        tracking=True
    )

    work_end = fields.Date(string="Work End",
        states=READONLY_STATES,
        tracking=True
    )

    fines_rate = fields.Monetary(string="Fines Rate",
        states=READONLY_STATES,
        tracking=True
    )

    fines_late = fields.Monetary(string="Fines Amount",
        help="Computed amount. Can be overwritten",
        states=READONLY_STATES,
        tracking=True
    )

    late_days = fields.Integer(string="Late Days",
        help="Late day(s) from Current Date - End Date",
        states=READONLY_STATES,
        tracking=True
    )

    contract_name = fields.Char(
        string="Contract Name",
        tracking=True,
        states=READONLY_STATES,
    )

    contract_number = fields.Char(
        string="Contract No.",
        tracking=True,
        states=READONLY_STATES,
    )

    is_construction = fields.Boolean(
        string="Is Construction",
        compute="_compute_is_construction",
        store=True,
    )

    _sql_constraints = [
        (
            "unique_contract_number",
            "unique(contract_number)",
            "The contract_number must be unique!",
        ),
    ]

    @api.depends("contract_type_id")
    def _compute_is_construction(self):
        for rec in self:
            rec.is_construction = bool(rec.contract_type_id.is_construction)

    def compute_fines_late(self):
        today = fields.Date.today()

        domain = [
            ('state', '=', 'order'),
            ('active', '=', True),
            '|',
                ('work_end', '>=', today),
                ('date_planned', '>=', today),
        ]

        orders = self.search(domain)

        for po in orders:
            po._compute_fines_internal()

    def _compute_fines_internal(self):
        today = fields.Date.today()

        for rec in self:
            rec.late_days = today - rec.end_date
            if rec.contract_type_id.is_construction:
                rec.end_date = rec.work_end

            else:
                rec.end_date = rec.date_planned

            rec.late_days = today - rec.end_date
            rec.fines_late = rec.fines_rate * rec.late_days

    def get_contract_number(self):
        source_map = {
            "r_prefix_ids": [
                self.env.ref("account_analytic_kmitl.source_2").id,
                self.env.ref("account_analytic_kmitl.source_4").id,
            ]
        }

        for rec in self:
            fy = rec.account_fiscal_year_id
            fiscal_year = fy.name if fy else fields.Date.today().strftime("%y")

            short_name = rec.department_id.short_name
            if not short_name:
                raise ValidationError(_("Department short name is missing."))

            prefix_src = "ร." if rec.source_analytic_id.id in source_map["r_prefix_ids"] else ""

            seq_code = f"purchase.contract.{fiscal_year}.{short_name}"

            Sequence = self.env['ir.sequence']
            if not Sequence.search([('code', '=', seq_code)], limit=1):
                Sequence.create({
                    'name': f'Purchase Contract {fiscal_year} {short_name}',
                    'code': seq_code,
                    'prefix': f'{short_name}. ',
                    'padding': 2,
                    'number_increment': 1,
                })

            next_num = Sequence.next_by_code(seq_code)
            rec.contract_number = f"{prefix_src}{next_num}/{fiscal_year}"

# -*- coding: utf-8 -*-
from datetime import date, datetime, time, timedelta

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

    date_planned_date = fields.Date(
        string="Expected Arrival (Date Only)",
        compute="_compute_date_only",
        inverse="_inverse_date_only",
        states=READONLY_STATES,
        store=False,
    )

    date_order_date = fields.Date(
        string="Order Date (Date Only)",
        compute="_compute_date_only",
        inverse="_inverse_date_only",
        states=READONLY_STATES,
        store=False,
    )

    _sql_constraints = [
        (
            "unique_contract_number",
            "unique(contract_number)",
            "The contract_number must be unique!",
        ),
    ]

    @api.depends("date_planned", "date_order")
    def _compute_date_only(self):
        for rec in self:
            rec.date_planned_date = rec.date_planned.date() if rec.date_planned else False
            rec.date_order_date = rec.date_order.date() if rec.date_order else False

    def _inverse_date_only(self):
        for rec in self:
            rec.date_planned = False
            rec.date_order = False

            if rec.date_planned_date:
                rec.date_planned = datetime.combine(
                    rec.date_planned_date,
                    time(0, 0, 0)
                )

            if rec.date_order_date:
                rec.date_order = datetime.combine(
                    rec.date_order_date,
                    time(0, 0, 0)
                )

    @api.depends("contract_type_id", "contract_type_id.is_construction")
    def _compute_is_construction(self):
        for rec in self:
            rec.is_construction = bool(rec.contract_type_id.is_construction)

    def _cron_compute_fines_late(self):
        today = fields.Date.today()

        domain = [
            ('state', '=', 'purchase'),
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
            if not rec.work_end or not rec.date_planned:
                rec.late_days = 0
                rec.fines_late = 0
                continue
            end_date = rec.work_end if rec.contract_type_id.is_construction else rec.date_planned.date()
            rec.late_days = (today - end_date).days
            rec.fines_late = rec.fines_rate * rec.late_days if rec.fines_rate else 0

    def _validate_get_contract_number(self):
        if not self.account_fiscal_year_id:
            raise ValidationError(_("Account fiscal year is required."))
        if not self.department_id or not self.department_id.short_name:
            raise ValidationError(_("Department's short name is required."))
        if not self.source_analytic_id:
            raise ValidationError(_("Source analytic is required."))

    def _get_next_contract_number(self):
        fiscal_year = self.account_fiscal_year_id.name
        short_name = self.department_id.short_name
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

        return Sequence.next_by_code(seq_code)

    def create_contract_number(self):
        prefix_src = "ร."
        source_analytic_ids = [
            self.env.ref("account_analytic_kmitl.source_2").id,
            self.env.ref("account_analytic_kmitl.source_4").id,
        ]

        for rec in self:
            rec._validate_get_contract_number()

            fiscal_year = rec.account_fiscal_year_id.name
            next_num = rec._get_next_contract_number()

            if rec.source_analytic_id.id in source_analytic_ids:
                rec.contract_number = f"{prefix_src}{next_num}/{fiscal_year}"
            else:
                rec.contract_number = f"{next_num}/{fiscal_year}"

# -*- coding: utf-8 -*-
import re
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
        tracking=True,
        default=fields.Date.today,
    )

    work_end = fields.Date(string="Work End",
        states=READONLY_STATES,
        tracking=True,
        compute="_compute_work_end",
        store=True,
    )

    work_end_display = fields.Char(
        string="Work End",
        compute='_compute_work_end_display',
        store=False,
    )

    fines_rate = fields.Monetary(string="Fines Rate",
        states=READONLY_STATES,
        tracking=True
    )

    fines_late = fields.Monetary(string="Fines Amount",
        help="Computed amount. Can be overwritten",
        states=READONLY_STATES,
        tracking=True,
        copy=False,
    )

    late_days = fields.Integer(string="Late Days",
        help="Late day(s) from Current Date - End Date",
        states=READONLY_STATES,
        tracking=True,
        copy=False,
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
        copy=False,
    )

    date_order_date = fields.Date(
        string="Order Date (Date Only)",
        compute="_compute_date_only",
        inverse="_inverse_date_only",
        states=READONLY_STATES,
        store=False,
    )

    contract_period_days = fields.Integer(
        string="Contract Period Days",
        tracking=True,
        states=READONLY_STATES,
    )

    supervision_cost = fields.Monetary(
        string="Supervision Cost",
        help="ถ้าไม่มีไม่ต้องกรอก",
        tracking=True,
        states=READONLY_STATES,
    )

    _sql_constraints = [
        (
            "unique_contract_number",
            "unique(contract_number)",
            "The contract_number must be unique!",
        ),
    ]

    @api.onchange("contract_number")
    def _onchange_contract_number_normalize(self):
        if self.contract_number:
            self.contract_number = self.contract_number.replace(" ", "")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("contract_number"):
                vals["contract_number"] = vals["contract_number"].replace(" ", "")
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("contract_number"):
            vals["contract_number"] = vals["contract_number"].replace(" ", "")
        return super().write(vals)

    @api.onchange('date_order_date', 'work_start')
    def _onchange_sync_work_start(self):
        for rec in self:
            if rec.date_order_date and rec.work_start:
                if rec.date_order_date > rec.work_start:
                    rec.work_start = rec.date_order_date

    @api.depends('work_start', 'contract_period_days')
    def _compute_work_end(self):
        for rec in self:
            if rec.work_start and rec.contract_period_days is not None:
                rec.work_end = rec.work_start + timedelta(days=rec.contract_period_days)
            else:
                rec.work_end = False

    _CONTRACT_NUMBER_RE = re.compile(r"^[0-9๐-๙ก-ฮa-z.,/]+$")

    @api.constrains("contract_number")
    def _check_contract_number_chars(self):
        for rec in self:
            if rec.contract_number and not self._CONTRACT_NUMBER_RE.match(
                rec.contract_number
            ):
                raise ValidationError(
                    _(
                        'Contract number "%(value)s" contains invalid characters. '
                        "Only digits (0-9, ๐-๙), Thai consonants (ก-ฮ), "
                        "English letters (a-z), and the symbols . , / are allowed.",
                        value=rec.contract_number,
                    )
                )

    @api.constrains('contract_period_days')
    def _check_contract_period_days(self):
        for rec in self:
            if rec.contract_period_days < 0:
                raise ValidationError(_('Contract Period Days must be >= 0'))

    @api.onchange('date_order_date', 'work_start', 'work_end')
    def _onchange_dates(self):
        self._compute_fines_internal()

    @api.depends("date_order")
    def _compute_date_only(self):
        for rec in self:
            rec.date_order_date = rec.date_order.date() if rec.date_order else False

    def _inverse_date_only(self):
        for rec in self:
            if rec.date_order_date:
                rec.date_order = datetime.combine(
                    rec.date_order_date,
                    time(0, 0, 0)
                )

    def _cron_compute_fines_late(self):
        today = fields.Date.today()

        domain = [
            ('state', '=', 'purchase'),
            ('work_end', '<=', today),
        ]

        orders = self.search(domain)

        for po in orders:
            po._compute_fines_internal()

    def _compute_fines_internal(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.work_end:
                rec.late_days = 0
                rec.fines_late = 0
                continue
            rec.late_days = max((today - rec.work_end).days, 0)
            rec.fines_late = rec.fines_rate * rec.late_days if rec.fines_rate else 0

    @api.depends('work_end')
    def _compute_work_end_display(self):
        today = fields.Date.today()
        for rec in self:
            if rec.work_end:
                days = (rec.work_end - rec.work_start).days
                rec.work_end_display = rec.work_end.strftime('%d/%m/%Y') + f"({days})"
            else:
                rec.work_end_display = ''

    def action_view_wa(self):
        result = super().action_view_wa()
        result["context"]["default_date_due"] = self.work_end
        return result

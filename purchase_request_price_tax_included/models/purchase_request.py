# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    vat_included = fields.Selection(
        [("exclusive", "VAT Exclusive"), ("inclusive", "VAT Inclusive")],
        default="exclusive",
        compute="_compute_vat_included",
        required=True,
        store=True,
        readonly=False,
    )

    is_vat_editable = fields.Boolean(
        compute="_compute_is_vat_editable",
        readonly=True,
        store=False,
    )

    @api.depends("is_editable")
    def _compute_is_vat_editable(self):
        for rec in self:
            rec.is_vat_editable = rec.is_editable

    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        domain="[('type_tax_use', 'in', ['purchase']), ('company_id', '=', company_id)]",
        check_company=True,
        context={"active_test": False},
    )

    @api.depends('line_ids.price_total')
    def _amount_all(self):
        for record in self:
            line_ids = record.line_ids

            if record.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in line_ids
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(record.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(record.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(line_ids.mapped('price_subtotal'))
                amount_tax = sum(line_ids.mapped('price_tax'))

            record.amount_untaxed = amount_untaxed
            record.amount_tax = amount_tax
            record.amount_total = record.amount_untaxed + record.amount_tax

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=True)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    @api.depends("vat_included")
    def _compute_vat_included(self):
        for record in self:
            if record.vat_included == "exclusive":
                record.tax_id = False

    @api.onchange("vat_included")
    def onchange_vat_included(self):
        if self.vat_included == "inclusive":
            if self.tax_id:
                return
            default_tax = self.env["account.tax"].search(
                [
                    ("type_tax_use", "in", ["purchase"]),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            self.tax_id = default_tax.id
        else:
            self.tax_id = False

    @api.depends_context('lang')
    @api.depends('line_ids.tax_id', 'line_ids.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for record in self:
            line_ids = record.line_ids
            record.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in line_ids],
                record.currency_id or record.company_id.currency_id,
            )

import copy

from odoo import fields, models
from odoo.tools.misc import formatLang


class TaxAdjustmentMixin(models.AbstractModel):
    """Manual VAT adjustment on document totals, like the editable tax
    amount on vendor bills. The adjustment is kept as a delta per tax group
    on the document header so line prices are never touched.

    Inheriting models must:
    - redefine ``tax_totals`` with ``inverse="_inverse_tax_totals"``
    - override ``_compute_tax_adjustment`` with ``@api.depends`` on the line
      amounts (editing lines resets the adjustment, like on vendor bills)
    - call ``_apply_tax_adjustment_amounts`` / ``_apply_tax_adjustment_totals``
      after super() in ``_amount_all`` / ``_compute_tax_totals``
    """

    _name = "tax.adjustment.mixin"
    _description = "Tax Adjustment Mixin"

    tax_adjustment = fields.Json(
        compute="_compute_tax_adjustment",
        store=True,
        readonly=False,
        copy=False,
        help="Manual tax adjustment per tax group: {tax_group_id: delta}",
    )

    def _compute_tax_adjustment(self):
        self.tax_adjustment = {}

    def _get_tax_adjustment_currency(self):
        self.ensure_one()
        return self.currency_id or self.company_id.currency_id

    @staticmethod
    def _get_tax_group_amounts(tax_totals):
        return {
            str(group["tax_group_id"]): group["tax_group_amount"]
            for groups in (tax_totals or {}).get("groups_by_subtotal", {}).values()
            for group in groups
        }

    def _apply_tax_adjustment_amounts(self, fnames=("amount_tax", "amount_total")):
        for rec in self:
            delta = sum((rec.tax_adjustment or {}).values())
            if delta:
                for fname in fnames:
                    rec[fname] += delta

    def _apply_tax_adjustment_totals(self):
        for rec in self:
            adjustment = rec.tax_adjustment or {}
            if not adjustment or not rec.tax_totals:
                continue
            currency = rec._get_tax_adjustment_currency()
            totals = copy.deepcopy(rec.tax_totals)
            groups_by_subtotal = totals["groups_by_subtotal"]
            for groups in groups_by_subtotal.values():
                for group in groups:
                    delta = adjustment.get(str(group["tax_group_id"]))
                    if delta:
                        group["tax_group_amount"] += delta
                        group["formatted_tax_group_amount"] = formatLang(
                            self.env, group["tax_group_amount"], currency_obj=currency
                        )
            amount_total = totals["amount_untaxed"]
            for subtotal in totals["subtotals"]:
                subtotal["amount"] = amount_total
                subtotal["formatted_amount"] = formatLang(
                    self.env, amount_total, currency_obj=currency
                )
                amount_total += sum(
                    group["tax_group_amount"]
                    for group in groups_by_subtotal.get(subtotal["name"], [])
                )
            totals["amount_total"] = currency.round(amount_total)
            totals["formatted_amount_total"] = formatLang(
                self.env, amount_total, currency_obj=currency
            )
            rec.tax_totals = totals

    def _inverse_tax_totals(self):
        for rec in self:
            new_amounts = self._get_tax_group_amounts(rec.tax_totals)
            old_adjustment = rec.tax_adjustment or {}
            # tax_totals is protected during write(): call the compute directly
            # to get the totals from the lines + current adjustment
            rec._compute_tax_totals()
            current_amounts = self._get_tax_group_amounts(rec.tax_totals)
            currency = rec._get_tax_adjustment_currency()
            adjustment = {}
            for key, amount in current_amounts.items():
                delta = currency.round(
                    old_adjustment.get(key, 0.0) + new_amounts.get(key, amount) - amount
                )
                if not currency.is_zero(delta):
                    adjustment[key] = delta
            if adjustment != old_adjustment:
                rec.tax_adjustment = adjustment
                rec._compute_tax_totals()

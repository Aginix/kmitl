# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class ReceiptKmitl(models.Model):
    _inherit = "kmitl.receipt"

    def _get_revenue_splits(self, line):
        self.ensure_one()
        buckets = line.product_id.product_tmpl_id.receipt_allocation_line_ids
        if not buckets:
            return super()._get_revenue_splits(line)

        currency = self.currency_id
        fixed = buckets.filtered(lambda b: b.method == "fixed")
        percent = buckets.filtered(lambda b: b.method == "percent")
        fixed_total = sum(fixed.mapped("fixed_amount"))
        if float_compare(fixed_total, line.amount, precision_rounding=currency.rounding) > 0:
            raise UserError(
                _("Line '%(line)s': fixed allocation amounts (%(fixed)s) "
                  "exceed the line amount (%(amount)s).")
                % {
                    "line": line.name,
                    "fixed": fixed_total,
                    "amount": line.amount,
                }
            )
        remainder = line.amount - fixed_total

        splits = [
            self._build_allocation_split(line, bucket, bucket.fixed_amount)
            for bucket in fixed
        ]
        running = 0.0
        last_index = len(percent) - 1
        for index, bucket in enumerate(percent):
            if index == last_index:
                # Last percent bucket absorbs the rounding residual so
                # credits sum exactly to the line amount.
                amount = remainder - running
            else:
                amount = currency.round(remainder * bucket.percentage / 100.0)
                running += amount
            splits.append(self._build_allocation_split(line, bucket, amount))
        return splits

    def _build_allocation_split(self, line, bucket, amount):
        """Merge the line's own distribution with the bucket's overrides:
        drop the base entry for any plan code the bucket overrides, keep the
        rest, then add the bucket's own dimensions."""
        self.ensure_one()
        base_ids = [int(key) for key in (line.analytic_distribution or {})]
        base_accounts = self.env["account.analytic.account"].browse(base_ids)
        overridden_codes = {
            plan_code
            for plan_code, field_name in bucket._analytic_keys.items()
            if bucket[field_name]
        }
        distribution = {
            str(account.id): 100
            for account in base_accounts
            if account.plan_id.code not in overridden_codes
        }
        for plan_code, field_name in bucket._analytic_keys.items():
            analytic = bucket[field_name]
            if analytic:
                distribution[str(analytic.id)] = 100
        return {
            "account_id": bucket.account_id.id,
            "amount": amount,
            "analytic_distribution": distribution or False,
            "name": bucket.name,
        }

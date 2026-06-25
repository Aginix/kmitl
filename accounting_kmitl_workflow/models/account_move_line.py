# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

# Root analytic plan codes for the four printed accounting dimensions.
DIMENSION_CODES = ("departments", "sources", "funds", "activities")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _kmitl_resolve_dimensions(self):
        """Resolve this line's analytic_distribution (JSON) into the four named
        KMITL dimensions for the voucher report.

        account.move.line carries only ``analytic_distribution`` (no convenience
        ``*_analytic_id`` fields), so we map each analytic account to its root
        plan code (departments / sources / funds / activities).

        :return: dict keyed by root plan code -> analytic account display name.
        """
        self.ensure_one()
        result = {code: "" for code in DIMENSION_CODES}
        distribution = self.analytic_distribution or {}
        if not distribution:
            return result
        account_ids = [int(key) for key in distribution]
        accounts = self.env["account.analytic.account"].browse(account_ids)
        for account in accounts:
            code = account.root_plan_id.code
            if code in result:
                result[code] = account.display_name
        return result

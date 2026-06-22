import re

from odoo import api, fields, models
from odoo.osv import expression


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    # Search the hierarchical complete_name (e.g. "parent / child") so users can
    # find children by typing the parent's name. The stored complete_name from
    # account_analytic_parent already includes the account's own name as suffix.
    _rec_names_search = ["complete_name", "code"]

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        # name_get displays records as "[code] complete_name". When users edit
        # that text in an autocomplete (e.g. deleting the last hierarchy segment
        # to look for siblings), the leftover "[code]" prefix is not part of any
        # single stored field, so the default search matches nothing. Detect the
        # prefix, drop it, and search the code and the remaining hierarchical
        # name independently (OR) so siblings under the same parent are found.
        if name and operator not in expression.NEGATIVE_TERM_OPERATORS:
            match = re.match(r"^\s*\[(?P<code>[^\]]*)\]\s*(?P<rest>.*)$", name)
            if match:
                code = match.group("code").strip()
                rest = match.group("rest").strip()
                subdomains = []
                if rest:
                    subdomains.append([("complete_name", operator, rest)])
                if code:
                    subdomains.append([("code", operator, code)])
                if subdomains:
                    domain = expression.AND(
                        [list(args or []), expression.OR(subdomains)]
                    )
                    return self._search(
                        domain, limit=limit, access_rights_uid=name_get_uid
                    )
        return super()._name_search(
            name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid
        )

    department_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="account_analytic_department_rel",
        column1="src_id",
        column2="department_id",
        string="Departments",
        domain=lambda self: [
            (
                "plan_id",
                "=",
                self.env.ref("account_analytic_kmitl.analytic_plan_departments").id,
            )
        ],
    )
    fund_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="account_analytic_fund_rel",
        column1="src_id",
        column2="fund_id",
        string="Funds",
        domain=lambda self: [
            (
                "plan_id",
                "=",
                self.env.ref("account_analytic_kmitl.analytic_plan_funds").id,
            )
        ],
    )

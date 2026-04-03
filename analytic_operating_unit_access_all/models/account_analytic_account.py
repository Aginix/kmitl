from odoo import api, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        """Filter analytic accounts by user's Operating Units in dropdowns.

        By default, Many2one/Many2many dropdowns only show analytic accounts
        belonging to the user's OUs (or those with no OU assigned).

        Bypass methods (show all OUs):
        - User has group "Access all OUs' analytics"
        - XML: context="{'all_analytic_ou': True}" on the field
          e.g. <field name="department_analytic_id"
                      context="{'all_analytic_ou': True}" />
        - Python: record.with_context(all_analytic_ou=True).name_search(...)
        """
        args = args or []
        if not self.env.context.get(
            "all_analytic_ou"
        ) and not self.env.user.has_group(
            "analytic_operating_unit_access_all.group_all_ou_analytic"
        ):
            user_ou_ids = self.env.user.operating_unit_ids.ids
            if user_ou_ids:
                args = args + [
                    "|",
                    ("operating_unit_ids", "in", user_ou_ids),
                    ("operating_unit_ids", "=", False),
                ]
        return super()._name_search(
            name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid
        )

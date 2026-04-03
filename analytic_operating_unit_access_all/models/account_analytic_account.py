from odoo import api, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def _get_ou_domain(self):
        """Return OU filter domain for current user, or empty list to skip.

        Bypass methods (show all OUs):
        - User has group "Access all OUs' analytics"
        - XML: context="{'all_analytic_ou': True}" on the field
          e.g. <field name="department_analytic_id"
                      context="{'all_analytic_ou': True}" />
        - Python: record.with_context(all_analytic_ou=True).search(...)
        """
        if self.env.context.get(
            "all_analytic_ou"
        ) or self.env.user.has_group(
            "analytic_operating_unit_access_all.group_all_ou_analytic"
        ):
            return []
        user_ou_ids = self.env.user.operating_unit_ids.ids
        if not user_ou_ids:
            return []
        return [
            "|",
            ("operating_unit_ids", "in", user_ou_ids),
            ("operating_unit_ids", "=", False),
        ]

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = (args or []) + self._get_ou_domain()
        return super()._name_search(
            name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid
        )

    @api.model
    def web_search_read(
        self, domain=None, fields=None, offset=0, limit=None, order=None,
        count_limit=None,
    ):
        domain = (domain or []) + self._get_ou_domain()
        return super().web_search_read(
            domain, fields, offset=offset, limit=limit, order=order,
            count_limit=count_limit,
        )

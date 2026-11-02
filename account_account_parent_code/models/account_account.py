# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from collections import defaultdict

from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"
    _parent_store = True

    # Not a compute: adding or recoding one account can re-parent others
    # (e.g. a new header account adopts the existing accounts below it).
    parent_id = fields.Many2one(
        comodel_name="account.account",
        string="Parent Account",
        index=True,
        ondelete="set null",
        readonly=True,
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        comodel_name="account.account",
        inverse_name="parent_id",
        string="Child Accounts",
    )

    @api.model
    def _get_parent_account_code(self, code, codes):
        """Return the parent code of ``code`` among ``codes`` (stripped codes).

        Codes are zero-padded, so the significant part of an account code is
        the code without its trailing zeros (1112110000 -> 111211). The parent
        is the account whose significant part is the longest proper prefix of
        it: 1112110001 -> 1112110000 -> 1112000000 -> 1110000000 -> ...
        """
        for i in range(len(code) - 1, 0, -1):
            if code[:i] in codes:
                return code[:i]
        return None

    @api.model
    def _update_parent_accounts(self, companies):
        accounts = self.sudo().search([("company_id", "in", companies.ids)])
        by_company = defaultdict(lambda: self.browse())
        for account in accounts:
            by_company[account.company_id] |= account
        to_write = defaultdict(list)
        for company_accounts in by_company.values():
            codes = {}
            for account in company_accounts:
                codes.setdefault((account.code or "").rstrip("0"), account)
            for account in company_accounts:
                parent_code = self._get_parent_account_code(
                    (account.code or "").rstrip("0"), codes
                )
                parent = codes[parent_code] if parent_code else self.browse()
                if account.parent_id != parent:
                    to_write[parent.id].append(account.id)
        for parent_id, account_ids in to_write.items():
            self.sudo().browse(account_ids).write({"parent_id": parent_id})

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        self._update_parent_accounts(accounts.company_id)
        return accounts

    def write(self, vals):
        companies = self.company_id
        res = super().write(vals)
        if "code" in vals or "company_id" in vals:
            self._update_parent_accounts(companies | self.company_id)
        return res

    def unlink(self):
        companies = self.company_id
        res = super().unlink()
        self._update_parent_accounts(companies)
        return res

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementPaymentLine(models.Model):
    """Previews the cash route a payee's paying account would travel, at the
    point the auditor or the finance office actually chooses หัวจ่าย — not
    only later, as a non-blocking warning when the accounting maker submits
    the voucher's journal entry (``account.move._is_missing_cash_route``).

    Every field here is non-stored with ``compute_sudo=True``: the groups
    that use this tree (``group_disbursement_payment_auditor``,
    ``finance_kmitl.group_finance_kmitl_user_out``,
    ``group_disbursement_payment_finance``) hold no ACL on
    ``kmitl.cash.route`` at all — it is accounting's own master data — and
    opening it up for a read-only string is wider than this needs.
    """

    _inherit = "disbursement.payment.line"

    cash_route_id = fields.Many2one(
        comodel_name="kmitl.cash.route",
        string="Cash Route",
        compute="_compute_cash_route",
        compute_sudo=True,
        help="The route this payee's money would travel to reach the chosen "
        "paying account, if one is set up for it.",
    )
    cash_route_state = fields.Selection(
        selection=[
            ("routed", "Routed"),
            ("direct", "Direct"),
            ("missing", "Not Set Up"),
        ],
        string="Cash Route Status",
        compute="_compute_cash_route",
        compute_sudo=True,
        help="Routed: money travels through one or more intermediate "
        "accounts before reaching the paying account. Direct: the paying "
        "account is spent out of directly, by design. Not Set Up: no route "
        "exists yet for this paying account and source of funds — the "
        "voucher's entry will carry a non-blocking warning at Submit unless "
        "this is fixed first.",
    )
    cash_route_display = fields.Char(
        string="Cash Route",
        compute="_compute_cash_route",
        compute_sudo=True,
        help="The route's accounts, source to paying account, named the way "
        "the treasury office says them: bank abbreviation and the last "
        "digits of the account number.",
    )

    @api.depends("paying_account_id", "request_id.source_analytic_id", "company_id")
    def _compute_cash_route(self):
        Route = self.env["kmitl.cash.route"]
        for line in self:
            account = line.paying_account_id.payment_account_id
            source = line.request_id.source_analytic_id
            route = Route._for_account_and_source(account, source, line.company_id)
            line.cash_route_id = route
            if route:
                line.cash_route_state = "direct" if not route.hop_ids else "routed"
                line.cash_route_display = route._display_chain()
            elif Route._should_have_route(line.paying_account_id, source):
                line.cash_route_state = "missing"
                line.cash_route_display = False
            else:
                line.cash_route_state = False
                line.cash_route_display = False

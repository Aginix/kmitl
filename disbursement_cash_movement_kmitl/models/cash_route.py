# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CASH_ACCOUNT_DOMAIN = [
    ("account_type", "in", ("asset_cash", "asset_current")),
    ("deprecated", "=", False),
]


class KmitlCashRoute(models.Model):
    """Which accounts a disbursement voucher's money travels through on its
    way to a paying account (หัวจ่าย), keyed by (paying account × source of
    funds).

    KMITL never pays out of its main savings account directly: the bank
    auto-sweeps a single cheque covering many payees down through one or more
    intermediate current accounts before it reaches the account a voucher is
    actually drawn on. Accounting does not book that sweep when it happens —
    one cheque covers payees with different dimensions — so it is booked
    instead, per payee, at the moment each voucher's payable is cleared. A row
    existing is the rule: a (paying account, source) pair with no row is a
    setup gap, not "pays directly", which is instead said by a row whose
    ``hop_ids`` is empty.
    """

    _name = "kmitl.cash.route"
    _description = "Inter-account Cash Route"
    _order = "paying_gl_account_id"

    name = fields.Char(compute="_compute_name", store=True)
    paying_gl_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Paying Account",
        required=True,
        ondelete="restrict",
        check_company=True,
        domain=CASH_ACCOUNT_DOMAIN,
        help="หัวจ่าย — the GL account a voucher is drawn on. Named by GL "
        "account rather than by payment method line, so a transfer and a "
        "cheque out of the same bank account share one route.",
    )
    source_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        string="Sources of Funds",
        required=True,
        domain=[("root_plan_id.code", "=", "sources")],
        help="แหล่งเงิน — which sources this route applies to. Money from a "
        "government-budget source and an own-revenue source usually travels "
        "through different accounts even to the same paying account.",
    )
    hop_ids = fields.One2many(
        comodel_name="kmitl.cash.route.hop",
        inverse_name="route_id",
        string="Intermediate Accounts",
        help="บัญชีระหว่างทาง — the accounts money passes through, from the "
        "true source down to (but not including) the paying account, in "
        "order. Left empty on purpose for a paying account the money is "
        "spent directly out of.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    @api.depends("paying_gl_account_id", "source_analytic_ids")
    def _compute_name(self):
        for route in self:
            account = route.paying_gl_account_id
            sources = route.source_analytic_ids
            if account and sources:
                route.name = "%s (%s)" % (
                    account.name,
                    ", ".join(sources.mapped("name")),
                )
            else:
                route.name = account.name or _("New Cash Route")

    @api.constrains("paying_gl_account_id", "source_analytic_ids", "company_id")
    def _check_source_not_shared(self):
        """One route per (paying account, source of funds, company).

        A SQL unique constraint cannot span a many2many, so the same check is
        done here: two routes covering the same paying account with an
        overlapping source would leave ``_for_payment`` unable to tell which
        one applies.
        """
        for route in self:
            if not route.paying_gl_account_id or not route.source_analytic_ids:
                continue
            others = self.search(
                [
                    ("id", "!=", route.id),
                    ("paying_gl_account_id", "=", route.paying_gl_account_id.id),
                    ("company_id", "=", route.company_id.id),
                    ("source_analytic_ids", "in", route.source_analytic_ids.ids),
                ]
            )
            if others:
                raise ValidationError(
                    _(
                        "%(account)s already has a cash route for %(sources)s "
                        "(%(other)s). A source of funds may only reach one "
                        "paying account through one route.",
                        account=route.paying_gl_account_id.display_name,
                        sources=", ".join(
                            (route.source_analytic_ids & others.source_analytic_ids)
                            .mapped("name")
                        ),
                        other=", ".join(others.mapped("display_name")),
                    )
                )

    @api.constrains("paying_gl_account_id", "hop_ids")
    def _check_no_cycle(self):
        for route in self:
            if route.paying_gl_account_id in route.hop_ids.account_id:
                raise ValidationError(
                    _(
                        "%s cannot be both the paying account and one of its "
                        "own intermediate accounts."
                    )
                    % route.paying_gl_account_id.display_name
                )

    @api.model
    def _for_payment(self, payment):
        """The route this payment's money travels, empty if none is set up.

        Keyed by the paying account the voucher is actually drawn on
        (``outstanding_account_id``, which for a KMITL voucher is always the
        GL of its ``payment_method_line_id``) and the source of funds on the
        voucher itself. An empty result is not "pays directly" — that is a
        route whose ``hop_ids`` is empty — it is "nobody has set this up yet".
        """
        account = payment.outstanding_account_id
        source = payment.source_analytic_id
        if not account or not source:
            return self.browse()
        return self.search(
            [
                ("paying_gl_account_id", "=", account.id),
                ("source_analytic_ids", "=", source.id),
                ("company_id", "=", payment.company_id.id),
            ],
            limit=1,
        )

    def _leg_specs(self, amount_currency, balance):
        """Every cash-movement line this route produces, in ledger order:
        ``[(account, amount_currency, balance)]``.

        ``amount_currency``/``balance`` are the single net amount every leg
        moves — the same one already computed for the payment's liquidity
        line — so consecutive legs are a Dr/Cr mirror pair and the path nets
        to zero except at its two ends (the source account, credited once;
        the paying account, debited once).
        """
        self.ensure_one()
        # Built as a plain list, not by concatenating the recordset's own
        # Many2one values: accessing a relational field on more than one
        # record at once goes through ``mapped()``, which silently drops
        # duplicates — fine for the account *set* a route touches, wrong here
        # where the same account legitimately repeating in a longer chain
        # must still produce one leg per hop.
        path = [hop.account_id for hop in self.hop_ids.sorted("sequence")]
        path.append(self.paying_gl_account_id)
        amount_currency, balance = abs(amount_currency), abs(balance)
        specs = []
        for credit_account, debit_account in zip(path, path[1:]):
            specs.append((debit_account, amount_currency, balance))
            specs.append((credit_account, -amount_currency, -balance))
        return specs

    def _leg_vals(self, liquidity_vals, payment):
        """Full ``account.move.line`` create values for every leg, ready to
        append to the values ``_prepare_move_line_default_vals`` returns.

        ``liquidity_vals`` is the liquidity line's own create values — its
        amount is the net amount credited at the paying account, which is
        exactly what every leg reuses.
        """
        self.ensure_one()
        balance = liquidity_vals["debit"] - liquidity_vals["credit"]
        specs = self._leg_specs(liquidity_vals["amount_currency"], balance)
        vals = []
        for sequence, (account, amount_currency, leg_balance) in enumerate(specs):
            vals.append(
                {
                    "name": liquidity_vals["name"],
                    "date_maturity": liquidity_vals["date_maturity"],
                    "account_id": account.id,
                    "partner_id": payment.partner_id.id,
                    "currency_id": liquidity_vals["currency_id"],
                    "amount_currency": amount_currency,
                    "debit": leg_balance if leg_balance > 0 else 0.0,
                    "credit": -leg_balance if leg_balance < 0 else 0.0,
                    "analytic_distribution": payment.analytic_distribution,
                    "is_cash_movement_line": True,
                    "sequence": 200 + sequence,
                }
            )
        return vals


class KmitlCashRouteHop(models.Model):
    _name = "kmitl.cash.route.hop"
    _description = "Inter-account Cash Route — Intermediate Account"
    _order = "route_id, sequence, id"

    route_id = fields.Many2one(
        comodel_name="kmitl.cash.route",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        required=True,
        check_company=True,
        domain=CASH_ACCOUNT_DOMAIN,
    )
    company_id = fields.Many2one(related="route_id.company_id", store=True)

    @api.constrains("route_id", "account_id", "sequence")
    def _check_no_adjacent_duplicate(self):
        for route in self.mapped("route_id"):
            hops = route.hop_ids.sorted("sequence")
            for previous, current in zip(hops, hops[1:]):
                if previous.account_id == current.account_id:
                    raise ValidationError(
                        _(
                            "%s appears twice in a row in the same cash "
                            "route's intermediate accounts."
                        )
                        % current.account_id.display_name
                    )

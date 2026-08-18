# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.tools.misc import formatLang


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    cash_revenue_handover_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="cash_revenue_handover_request_id",
        string="Cash & Revenue Handover",
        readonly=True,
        copy=False,
    )
    cash_revenue_handover_count = fields.Integer(
        string="Handover Count",
        compute="_compute_cash_revenue_handover_count",
    )

    @api.depends(
        "cash_revenue_handover_move_ids",
        "cash_revenue_handover_move_ids.state",
    )
    def _compute_cash_revenue_handover_count(self):
        for record in self:
            record.cash_revenue_handover_count = len(
                record.cash_revenue_handover_move_ids.filtered(
                    lambda move: move.state != "cancel"
                )
            )

    # ------------------------------------------------------------------
    # Handover creation
    # ------------------------------------------------------------------
    def _create_bill(self):
        """Draft the handover alongside the bill(s), then leave it alone.

        Funding the unit is what makes the expense bookable, so the entry is
        drawn at the very moment the payable is registered — one per request,
        not per payee, because who is being paid has no bearing on which unit
        needs funding.

        It is left in ``draft`` on purpose: accounting reviews it and takes it
        through the usual Submit → Approve, and owns cancelling it too. Nothing
        here follows the request's lifecycle afterwards, so a cancelled request
        leaves its handover standing for accounting to reverse by hand.
        """
        bills = super()._create_bill()
        self._create_cash_revenue_handover()
        return bills

    def _create_cash_revenue_handover(self):
        """Create the draft entry moving central's cash and revenue to this unit.

        Every reason not to is a silent skip, not an error: none of them means
        anything is wrong with the disbursement, and refusing to bill a
        perfectly good request because no profile is configured would be worse
        than booking the expense unfunded.
        """
        self.ensure_one()
        funding = self.env["kmitl.central.funding"]._for_request(self)
        no_move = self.env["account.move"]
        if not funding:
            # not money held centrally — nothing to hand over
            return no_move
        if funding.covers_department(self.department_analytic_id):
            # already spending where the money is held
            return no_move
        if self.cash_revenue_handover_move_ids.filtered(
            lambda move: move.state != "cancel"
        ):
            # already funded; keeps a re-run from double-funding the unit
            return no_move
        amount = self._cash_revenue_handover_amount()
        if self.company_id.currency_id.compare_amounts(amount, 0.0) <= 0:
            return no_move

        line_specs = self._cash_revenue_handover_line_specs(funding, amount)
        move = self.env["account.move"].create(
            self._prepare_cash_revenue_handover_vals(funding, line_specs)
        )
        self._apply_handover_line_distribution(move, line_specs)
        self.message_post(
            body=_(
                'Cash &amp; revenue handover of %(amount)s '
                '<a href="%(link)s" target="_blank">drafted</a> for %(unit)s.'
            )
            % {
                "amount": formatLang(
                    self.env, amount, currency_obj=self.company_id.currency_id
                ),
                "link": "/web#id=%d&model=account.move&view_type=form" % move.id,
                "unit": self.department_analytic_id.display_name,
            },
            subtype_xmlid="mail.mt_note",
        )
        return move

    def _cash_revenue_handover_amount(self):
        """The gross request total, in company currency.

        Gross rather than net of withholding tax: it is what the budget ledger
        consumes, and it is the figure that leaves the unit's profit and loss at
        zero — the withheld part stays with the unit as cash against the
        withholding liability it now carries, until central remits it.
        """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if self.currency_id == company_currency:
            return self.amount_total
        return self.currency_id._convert(
            self.amount_total, company_currency, self.company_id, self.date
        )

    def _cash_revenue_handover_line_specs(self, funding, amount):
        """``(account, debit, credit, distribution)`` for the four lines, in order."""
        self.ensure_one()
        central = self._central_analytic_distribution(funding)
        unit = self.analytic_distribution
        return [
            # central gives up the cash and the revenue it recognised
            (funding.bank_account_id, 0.0, amount, central),
            (funding.revenue_account_id, amount, 0.0, central),
            # the unit recognises both under its own dimensions
            (funding.revenue_account_id, 0.0, amount, unit),
            (funding.bank_account_id, amount, 0.0, unit),
        ]

    def _prepare_cash_revenue_handover_vals(self, funding, line_specs):
        """The four-line entry: undo central's recognition, redo it at the unit.

        The header carries the request's **own** dimensions, so the entry reads as
        "this funds that request" and the four dimension fields the move form
        marks required are filled — an entry with them blank cannot be saved from
        the form at all. Its lines are then put right by
        ``_apply_handover_line_distribution``.
        """
        self.ensure_one()
        label = _("Cash & revenue handover: %s") % self.name
        return {
            "move_type": "entry",
            "journal_id": funding.journal_id.id,
            "date": self.date,
            "ref": label,
            "company_id": self.company_id.id,
            "cash_revenue_handover_request_id": self.id,
            "analytic_distribution": self.analytic_distribution,
            "line_ids": [
                Command.create(
                    {
                        "name": label,
                        "account_id": account.id,
                        "debit": debit,
                        "credit": credit,
                        "analytic_distribution": distribution,
                    }
                )
                for account, debit, credit, distribution in line_specs
            ],
        }

    def _apply_handover_line_distribution(self, move, line_specs):
        """Write each side's dimensions back onto the lines, after create.

        Odoo calls a field's ``inverse`` for any value handed to ``create``,
        whether or not the field is computed (``models.py`` ``create``), and it
        does so once the rows exist — so ``accounting_kmitl``'s inverse has by
        then copied the header distribution onto all four lines, collapsing both
        sides of the handover onto one set of dimensions and leaving an entry
        that moves nothing. The two sides are therefore re-asserted here.

        Lines come back in creation order, which is the order of ``line_specs``.
        """
        self.ensure_one()
        for line, spec in zip(move.line_ids.sorted("id"), line_specs):
            line.analytic_distribution = spec[3]

    def _central_analytic_distribution(self, funding):
        """Central's side of the entry.

        The profile's department, fund and activity — all three fixed, because
        central parks every receipt of a source on the same three, whatever the
        money is later spent on — plus the request's own source of funds, since a
        handover never crosses แหล่งเงิน (the rule budget transfers already
        follow).
        """
        self.ensure_one()
        accounts = (
            funding.central_department_analytic_id
            | funding.central_fund_analytic_id
            | funding.central_activity_analytic_id
            | self.source_analytic_id
        )
        return {str(account.id): 100.0 for account in accounts}

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------
    def action_view_cash_revenue_handover(self):
        self.ensure_one()
        moves = self.cash_revenue_handover_move_ids
        if len(moves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Cash & Revenue Handover"),
                "res_model": "account.move",
                "res_id": moves.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Cash & Revenue Handover"),
            "res_model": "account.move",
            "domain": [("id", "in", moves.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

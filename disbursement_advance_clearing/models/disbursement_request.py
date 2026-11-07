# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, _, _lt, api, fields, models
from odoo.exceptions import UserError

ACCOUNTING_GROUP = "accounting_kmitl.group_accounting_kmitl_user"

CREATE_ACT = "disbursement.create_advance_clearing"
CONFIRM_ACT = "disbursement.confirm_advance_clearing"
# The bill-and-pay acts a request that pays no money out has nothing to do with.
PAYING_ACTS = (
    "disbursement.create_bill",
    "disbursement.confirm_bill",
    "disbursement.audit_payment",
    "disbursement.authorize_payment",
    "disbursement.confirm_paid",
)


class DisbursementRequest(models.Model):
    """A request that pays no money out (an advance, ``pays_out`` false) books
    the spending against the borrower's advance receivable: the accounting office
    raises a clearing entry (Dr expense / Cr ลูกหนี้เงินยืม) in the clearing
    journal instead of a bill, then confirms it once posted (ADR 0009)."""

    _inherit = "disbursement.request"

    advance_clearing_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="advance_clearing_request_id",
        string="Advance Clearing Entries",
        readonly=True,
        copy=False,
    )
    advance_clearing_count = fields.Integer(compute="_compute_advance_clearing_count")
    advance_clearing_confirmer_id = fields.Many2one(
        "res.users", string="Clearing Confirmed By", copy=False, readonly=True
    )
    advance_clearing_confirm_date = fields.Datetime(
        string="Clearing Confirmed On", copy=False, readonly=True
    )
    can_create_advance_clearing = fields.Boolean(
        compute="_compute_can_advance_clearing"
    )
    can_confirm_advance_clearing = fields.Boolean(
        compute="_compute_can_advance_clearing"
    )

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": CREATE_ACT,
                "name": _lt("Create Advance Clearing Entry"),
                "kind": "act",
                "group": ACCOUNTING_GROUP,
                "sequence": 53,
                "module": "disbursement_advance_clearing",
            },
            {
                "code": CONFIRM_ACT,
                "name": _lt("Confirm Advance Cleared"),
                "kind": "act",
                "group": ACCOUNTING_GROUP,
                "sequence": 56,
                "module": "disbursement_advance_clearing",
            },
        ]

    def _disbursement_act_applicable(self, code):
        if code in PAYING_ACTS and not self.pays_out:
            return False
        if code in (CREATE_ACT, CONFIRM_ACT) and self.pays_out:
            return False
        return super()._disbursement_act_applicable(code)

    def _disbursement_act_offered(self, code):
        return self._disbursement_act_applicable(code) and super()._disbursement_act_offered(
            code
        )

    def _disbursement_check_act(self, code):
        super()._disbursement_check_act(code)
        for rec in self:
            if not rec._disbursement_act_applicable(code):
                raise UserError(
                    _("This act does not apply to request %s.") % rec.display_name
                )

    def _live_advance_clearing_moves(self):
        return self.advance_clearing_move_ids.filtered(lambda m: m.state != "cancel")

    @api.depends("advance_clearing_move_ids.state")
    def _compute_advance_clearing_count(self):
        for rec in self:
            rec.advance_clearing_count = len(rec._live_advance_clearing_moves())

    @api.depends("state", "pays_out", "advance_clearing_move_ids.state",
                 "advance_clearing_confirmer_id")
    @api.depends_context("uid")
    def _compute_can_advance_clearing(self):
        for rec in self:
            live = rec._live_advance_clearing_moves()
            rec.can_create_advance_clearing = not live and rec._disbursement_act_offered(
                CREATE_ACT
            )
            rec.can_confirm_advance_clearing = bool(
                live
                and not rec.advance_clearing_confirmer_id
                and rec._disbursement_act_offered(CONFIRM_ACT)
            )

    # ------------------------------------------------------------------
    # Settlement: billed once the entry is posted, booked once confirmed
    # ------------------------------------------------------------------
    def init(self):
        super().init()
        # An upgrade of a module below recomputes the stage without this
        # override: recompute it from the clearing entries.
        self.env.add_to_compute(
            self._fields["settlement_stage"],
            self.with_context(active_test=False).search([("payment_type", "!=", "direct")]),
        )

    @api.depends(
        "payment_type", "advance_clearing_move_ids.state", "advance_clearing_confirmer_id"
    )
    def _compute_settlement_stage(self):
        super()._compute_settlement_stage()
        for rec in self.filtered(lambda r: not r.pays_out):
            live = rec._live_advance_clearing_moves()
            if live and all(m.state == "posted" for m in live):
                rec.settlement_stage = (
                    "booked" if rec.advance_clearing_confirmer_id else "billed"
                )

    def _can_edit_blocked(self, kind):
        """An entry, even a draft one, was raised from the lines and dimensions."""
        return super()._can_edit_blocked(kind) or (
            kind in ("lines", "dimensions", "budget")
            and bool(self._live_advance_clearing_moves())
        )

    # ------------------------------------------------------------------
    # The acts
    # ------------------------------------------------------------------
    def action_create_advance_clearing(self):
        self.ensure_one()
        self._disbursement_check_act(CREATE_ACT)
        if self._live_advance_clearing_moves():
            raise UserError(
                _("Cancel the existing clearing entry before creating a new one.")
            )
        move = self.env["account.move"].create(self._prepare_advance_clearing_vals())
        self._disbursement_act_done(CREATE_ACT)
        self.message_post(
            body=_("Advance clearing entry %s created.") % move._get_html_link(),
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def _prepare_advance_clearing_vals(self):
        """Dr each line's expense, with its dimensions; Cr the advance receivable
        once per borrower."""
        self.ensure_one()
        company = self.company_id
        journal = company.advance_clearing_journal_id
        receivable = company.advance_clearing_account_id
        if not journal or not receivable:
            raise UserError(
                _(
                    "Set the advance clearing journal and the advance receivable "
                    "account in Settings first."
                )
            )
        if self.line_ids.filtered(lambda line: line.tax_ids or line.wht_tax_id):
            raise UserError(
                _("A request that clears an advance cannot carry taxes.")
            )
        lines = [
            Command.create(
                {
                    "name": line.name,
                    "account_id": line.account_id.id,
                    "partner_id": line.partner_id.id,
                    "debit": line.amount,
                    "analytic_distribution": line.analytic_distribution
                    or self.analytic_distribution,
                }
            )
            for line in self.line_ids
        ]
        for partner in self.line_ids.partner_id:
            amount = sum(
                self.line_ids.filtered(lambda line: line.partner_id == partner).mapped(
                    "amount"
                )
            )
            lines.append(
                Command.create(
                    {
                        "name": _("Advance clearing %s") % self.name,
                        "account_id": receivable.id,
                        "partner_id": partner.id,
                        "credit": amount,
                    }
                )
            )
        return {
            "move_type": "entry",
            "journal_id": journal.id,
            "date": fields.Date.context_today(self),
            "ref": self.name,
            "advance_clearing_request_id": self.id,
            "analytic_distribution": self.analytic_distribution,
            "line_ids": lines,
        }

    def action_confirm_advance_clearing(self):
        """The act: confirm the clearing entry is posted. It changes no state."""
        for rec in self:
            rec._disbursement_check_act(CONFIRM_ACT)
            live = rec._live_advance_clearing_moves()
            if not live:
                raise UserError(_("Create the clearing entry first."))
            unposted = live.filtered(lambda m: m.state != "posted")
            if unposted:
                raise UserError(
                    _("These entries are not posted yet: %s")
                    % ", ".join(unposted.mapped("display_name"))
                )
            rec.write(
                {
                    "advance_clearing_confirmer_id": self.env.user.id,
                    "advance_clearing_confirm_date": fields.Datetime.now(),
                }
            )
            rec._disbursement_act_done(CONFIRM_ACT)
        return True

    def action_view_advance_clearing(self):
        self.ensure_one()
        moves = self._live_advance_clearing_moves()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Advance Clearing Entries"),
            "res_model": "account.move",
            "target": "current",
        }
        if len(moves) == 1:
            action.update(res_id=moves.id, view_mode="form")
        else:
            action.update(domain=[("id", "in", moves.ids)], view_mode="tree,form")
        return action

    def _clear_advance_clearing_confirmation(self):
        self.filtered("advance_clearing_confirmer_id").write(
            {"advance_clearing_confirmer_id": False, "advance_clearing_confirm_date": False}
        )

    def action_draft(self):
        res = super().action_draft()
        self._clear_advance_clearing_confirmation()
        return res

    def _on_settlement_walked_back(self, previous_stage):
        """The entry is no longer posted: its confirmation no longer holds."""
        super()._on_settlement_walked_back(previous_stage)
        if not self.pays_out and self.settlement_stage == "none":
            self._clear_advance_clearing_confirmation()

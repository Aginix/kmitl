# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.osv import expression


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    bill_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="disbursement_request_id",
        string="Vendor Bills",
        readonly=True,
        copy=False,
    )

    bill_count = fields.Integer(
        string="Bill Count",
        compute="_compute_bill_count",
    )

    can_create_bill = fields.Boolean(compute="_compute_can_create_bill")

    move_line_count = fields.Integer(
        string="Move Line Count",
        compute="_compute_move_line_count",
    )

    # Every account.move tied to a request — direct bill, cash & revenue
    # handover, payment clearing — collected in one place so one smart button
    # replaces the three that used to live on each bridge.
    related_move_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_related_move_ids",
        string="Related Journal Entries",
    )
    related_move_count = fields.Integer(
        compute="_compute_related_move_ids",
        string="Related Move Count",
    )

    @api.depends("bill_ids", "bill_ids.state")
    def _compute_bill_count(self):
        """Number of non-cancelled bills linked to this request."""
        for record in self:
            record.bill_count = len(
                record.bill_ids.filtered(lambda b: b.state != "cancel")
            )

    @api.depends("bill_ids", "bill_ids.state", "bill_ids.line_ids")
    def _compute_move_line_count(self):
        for rec in self:
            active = rec.bill_ids.filtered(lambda b: b.state != "cancel")
            rec.move_line_count = len(
                active.line_ids.filtered(
                    lambda line: line.display_type not in ("line_section", "line_note")
                )
            )

    def _related_move_domain(self):
        """OR domain over every Many2one on account.move that ties a move to a
        request. Introspection means bridges downstream (handover, finance)
        contribute without this module depending on them, and any new linking
        field is picked up automatically.
        """
        self.ensure_one()
        Move = self.env["account.move"]
        leaves = [
            [(name, "=", self.id)]
            for name, field in Move._fields.items()
            if field.type == "many2one" and field.comodel_name == "disbursement.request"
        ]
        if not leaves:
            return [("id", "=", 0)]
        return expression.OR(leaves)

    def _compute_related_move_ids(self):
        Move = self.env["account.move"]
        for rec in self:
            moves = Move.search(
                expression.AND(
                    [
                        rec._related_move_domain(),
                        [("state", "!=", "cancel")],
                    ]
                )
            )
            rec.related_move_ids = moves
            rec.related_move_count = len(moves)

    # ------------------------------------------------------------------
    # Settlement stage: the bill leg
    # ------------------------------------------------------------------
    def init(self):
        super().init()
        # The column was filled with "none" when core was installed or upgraded,
        # before this override was loaded: recompute it from the bills.
        self.env.add_to_compute(
            self._fields["settlement_stage"],
            self.with_context(active_test=False).search([]),
        )

    @api.depends("bill_ids", "bill_ids.state")
    def _compute_settlement_stage(self):
        """Billed once every active bill is posted. Read from ``bill_ids``,
        never from ``related_move_ids``, so a cash and revenue handover never
        counts as a bill."""
        super()._compute_settlement_stage()
        for rec in self:
            active = rec.bill_ids.filtered(lambda b: b.state != "cancel")
            if active and all(b.state == "posted" for b in active):
                rec.settlement_stage = "billed"

    @api.depends("bill_ids", "bill_ids.state")
    def _compute_can_edit(self):
        super()._compute_can_edit()

    def _can_edit_blocked(self, kind):
        """A bill, even a draft one, was raised from the lines, the dimensions
        and the budget: they are frozen until it is cancelled."""
        return super()._can_edit_blocked(kind) or (
            kind in ("lines", "dimensions", "budget")
            and any(bill.state != "cancel" for bill in self.bill_ids)
        )

    def _on_bills_posted(self):
        """Every active bill of the request is now posted. Bridges hang what
        follows a posted bill on this (the payment lines)."""

    # ------------------------------------------------------------------
    # The create-bill act
    # ------------------------------------------------------------------
    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.create_bill",
                "name": _lt("Create Bill"),
                "kind": "act",
                "group": "accounting_kmitl.group_accounting_kmitl_user",
                # Money can walk back after the circuit is done: a bill may be
                # raised again then.
                "states": ("signed", "in_progress", "done"),
                "sequence": 50,
                "module": "disbursement_accounting_kmitl",
            }
        ]

    @api.depends("state", "bill_ids.state")
    @api.depends_context("uid")
    def _compute_can_create_bill(self):
        for rec in self:
            rec.can_create_bill = rec._disbursement_act_offered(
                "disbursement.create_bill"
            ) and not any(bill.state != "cancel" for bill in rec.bill_ids)

    # ------------------------------------------------------------------
    # Bill creation
    # ------------------------------------------------------------------
    def _create_bill(self):
        """Create vendor bill(s) from disbursement request."""
        self.ensure_one()

        if self.state == "cancel":
            raise UserError(_("A cancelled request cannot be billed."))

        bills = self._create_bills()

        for bill in bills:
            bill_link = "/web#id=%d&model=account.move&view_type=form" % bill.id
            self.message_post(
                body=_(
                    'Vendor Bill <a href="%(link)s" target="_blank">'
                    "%(name)s</a> has been created."
                )
                % {"link": bill_link, "name": bill.name},
                subtype_xmlid="mail.mt_note",
            )

        return bills

    def _create_bills(self):
        """Group lines by partner, create one bill per partner.

        Every disbursement request pays a name list (multi-partner), so bills
        are always split per recipient partner.
        """
        self.ensure_one()
        partner_lines = {}
        for line in self.line_ids:
            partner_lines.setdefault(
                line.partner_id,
                self.env["disbursement.request.line"],
            )
            partner_lines[line.partner_id] |= line

        bills = self.env["account.move"]
        for partner, lines in partner_lines.items():
            invoice_lines = [
                Command.create(self._prepare_bill_line_vals(line)) for line in lines
            ]
            partner_bank = lines[0].partner_bank_id
            bill = self.env["account.move"].create(
                self._prepare_bill_vals(partner, partner_bank, invoice_lines)
            )
            bills |= bill
        return bills

    def _prepare_bill_vals(self, partner, partner_bank, invoice_lines):
        """Prepare values for creating a vendor bill."""
        return {
            "disbursement_request_id": self.id,
            "partner_id": partner.id,
            "partner_bank_id": partner_bank.id if partner_bank else False,
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "ref": self.name,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "invoice_line_ids": invoice_lines,
            "analytic_distribution": self.analytic_distribution,
        }

    def _prepare_bill_line_vals(self, line):
        """Prepare values for a single invoice line.

        The request line's withholding tax is stamped directly at create time
        so it cannot be mis-assigned by a positional match against the created
        bill lines.
        """
        return {
            "name": line.name,
            "account_id": line.account_id.id,
            "quantity": 1.0,
            "price_unit": line.amount,
            "tax_ids": [Command.set(line.tax_ids.ids)],
            "wht_tax_id": line.wht_tax_id.id,
            "analytic_distribution": line.analytic_distribution,
        }

    # ------------------------------------------------------------------
    # Tier-gated actions
    # ------------------------------------------------------------------
    def action_create_bill(self):
        self.ensure_one()
        self._disbursement_check_act("disbursement.create_bill")
        existing_bills = self.bill_ids.filtered(lambda b: b.state != "cancel")
        if existing_bills:
            raise UserError(
                _(
                    "Cannot create new bill: existing bill(s) %s are still "
                    "in progress. Cancel them first before creating a new one."
                )
                % ", ".join(existing_bills.mapped("name"))
            )
        bills = self._create_bill()
        self._disbursement_act_done("disbursement.create_bill")
        if len(bills) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": bills.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bills"),
            "res_model": "account.move",
            "domain": [("id", "in", bills.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_post_bills(self):
        """Post all unposted bills.

        Programmatic/demo entry point only — it posts bills directly, bypassing
        the account.move approval. In the UI bills are posted by approving them
        on the account.move (Approve = post); there is no "Post Bills" button.
        The request's settlement stage follows the bills by itself.
        """
        for record in self:
            unposted_bills = record.bill_ids.filtered(
                lambda b: b.state in ("draft", "submitted")
            )
            if not unposted_bills:
                raise UserError(_("No bills to post."))
            unposted_bills.action_post()
        return True

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------
    def action_view_move_lines(self):
        """Open a tree of move.line aggregated from this DR's active bills."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "disbursement_accounting_kmitl.action_disbursement_move_lines"
        )
        action["domain"] = [
            ("move_id", "in", self.bill_ids.ids),
            ("move_id.state", "!=", "cancel"),
            ("display_type", "not in", ("line_section", "line_note")),
        ]
        action["context"] = {
            "default_disbursement_request_id": self.id,
        }
        return action

    def action_view_related_moves(self):
        """Open every account.move tied to this request in one place."""
        self.ensure_one()
        moves = self.related_move_ids
        if len(moves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Journal Entry"),
                "res_model": "account.move",
                "res_id": moves.id,
                "view_mode": "form",
                "target": "current",
            }
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "disbursement_accounting_kmitl.action_disbursement_related_moves"
        )
        action["domain"] = [("id", "in", moves.ids)]
        return action

    def action_cancel(self):
        """Block cancel if any bill is posted; cancel draft bills first."""
        for record in self:
            if record.state == "cancel":
                continue
            posted_bills = record.bill_ids.filtered(lambda b: b.state == "posted")
            if posted_bills:
                raise UserError(
                    _(
                        "Cannot cancel: bill(s) %s already posted. "
                        "Reverse the bill(s) first."
                    )
                    % ", ".join(posted_bills.mapped("name"))
                )
            draft_bills = record.bill_ids.filtered(lambda b: b.state == "draft")
            if draft_bills:
                draft_bills.button_cancel()
        return super().action_cancel()

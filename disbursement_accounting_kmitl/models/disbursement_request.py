# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
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

    def _on_bills_posted(self):
        """Hook: every active bill of the request is now posted."""

    def action_post_bills(self):
        """Post all unposted bills.

        Programmatic/demo entry point only — it posts bills directly, bypassing
        the account.move approval. In the UI bills are posted by approving them
        on the account.move (Approve = post); there is no "Post Bills" button.
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

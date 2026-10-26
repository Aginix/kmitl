# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, _lt, api, models

_logger = logging.getLogger(__name__)

# The parts of the document a station may let its people edit. They are
# permissions, not acts (``kind="edit"``): they are never required and never
# recorded as done. Core's ``can_edit_*`` flags read them.
_EDIT_KINDS = {
    "header": _lt("Edit the Header"),
    "lines": _lt("Edit the Lines"),
    "attachments": _lt("Edit the Attachments"),
    "dimensions": _lt("Edit the Dimensions"),
    "budget": _lt("Edit the Budget"),
}


class DisbursementRequest(models.Model):
    """Plugs the DR into the station engine through the core seams: signing
    enters the circuit, forwarding out of the last station completes it, and
    who may act, edit or take the request out is decided by the station
    holding it."""

    _name = "disbursement.request"
    _inherit = ["disbursement.request", "work.center.mixin"]

    # ------------------------------------------------------------------
    # Acts and editable parts
    # ------------------------------------------------------------------
    @api.model
    def _work_center_acts(self):
        edits = [
            {
                "code": "disbursement.edit_" + kind,
                "name": name,
                "kind": "edit",
                "group": "disbursement.group_disbursement_officer",
                "sequence": 100 + index,
                "module": "disbursement_work_center",
            }
            for index, (kind, name) in enumerate(_EDIT_KINDS.items())
        ]
        return super()._work_center_acts() + self._disbursement_acts() + edits

    def _work_center_act_applies(self, code):
        return self._disbursement_act_applicable(code)

    def _disbursement_act_offered(self, code):
        if self.state == "in_progress":
            return self._work_center_offers(code)
        return super()._disbursement_act_offered(code)

    def _disbursement_check_act(self, code):
        super()._disbursement_check_act(code)
        for rec in self.filtered(lambda r: r.state == "in_progress"):
            rec._work_center_check_act(code)

    def _disbursement_act_done(self, code):
        super()._disbursement_act_done(code)
        for rec in self:
            rec._work_center_act_done(code)

    def _disbursement_check_send_back(self):
        if self.state == "in_progress":
            return self._work_center_check_move()
        return super()._disbursement_check_send_back()

    # ------------------------------------------------------------------
    # Entering and leaving the circuit
    # ------------------------------------------------------------------
    @api.model
    def _work_center_circuit_domain(self):
        return [("state", "=", "in_progress")]

    def _on_signed(self):
        """Signed (or resubmitted after a correction): enter the circuit at the
        first station. Without a route the request stays signed."""
        super()._on_signed()
        for rec in self:
            if not rec._work_center_route():
                _logger.warning(
                    "No standard route for disbursement requests: %s stays signed.",
                    rec.display_name,
                )
                continue
            # In progress first, so the arrival hooks see the state they expect.
            rec.state = "in_progress"
            # sudo: the Saraban head who signs may not read the stations; the
            # signer is still recorded as the mover.
            rec.sudo()._work_center_enter(
                "resubmit" if rec.env.context.get("disbursement_resubmit") else "enter"
            )

    def _work_center_on_exit(self):
        self.state = "done"

    def _work_center_on_send_back(self, reason):
        # A DR's own send-back is the Return wizard; this keeps the engine's
        # generic one ending the same way.
        self.sudo()._action_return_for_edit(reason)

    def action_draft(self):
        """Core checks who may and resets the request; the station is left
        afterwards, because the check reads the station holding it."""
        res = super().action_draft()
        context = self.env.context
        for rec in self:
            rec._work_center_leave(
                context.get("work_center_departure", "send_back"),
                context.get("work_center_reason"),
            )
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for rec in self:
            rec._work_center_leave("cancel")
        return res

    # ------------------------------------------------------------------
    # Locks
    # ------------------------------------------------------------------
    @api.depends("work_center_id", "settlement_stage")
    def _compute_can_edit(self):
        super()._compute_can_edit()

    def _can_edit_open(self, kind):
        """A station also opens the parts it lists, until the money has started."""
        return super()._can_edit_open(kind) or (
            self.state == "in_progress"
            and self.settlement_stage == "none"
            and self._work_center_offers("disbursement.edit_" + kind)
        )

    # ------------------------------------------------------------------
    # The money walking back after the circuit is done
    # ------------------------------------------------------------------
    def _on_settlement_walked_back(self, previous_stage):
        """A finished request whose money went back a step (a bill reset, a
        cheque bounced) stays done; the people of the station that last
        approved it get a Todo to see to it."""
        super()._on_settlement_walked_back(previous_stage)
        stages = dict(self._fields["settlement_stage"]._description_selection(self.env))
        walked_back = self.env.ref(
            "disbursement_work_center.mail_activity_dr_money_walked_back"
        )
        for rec in self.filtered(lambda r: r.state == "done"):
            station = rec._work_center_last_visit().work_center_id
            if not station:
                continue
            users, _source = station._responsible_users()
            # A voucher cancelled through its payment and its move fires the
            # hook twice for the one walk back: one Todo per person is enough.
            pending = rec.sudo().activity_ids.filtered(
                lambda a: a.activity_type_id == walked_back
            ).user_id
            for user in users - pending:
                rec.sudo().activity_schedule(
                    "disbursement_work_center.mail_activity_dr_money_walked_back",
                    user_id=user.id,
                    note=_("The money went back from %(previous)s to %(current)s.")
                    % {
                        "previous": stages[previous_stage],
                        "current": stages[rec.settlement_stage],
                    },
                )

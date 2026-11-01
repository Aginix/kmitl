# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, _lt, api, models
from odoo.exceptions import AccessError, UserError

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

    def _verification_officer(self):
        """The return To-Dos reach the person handling the request at its
        station."""
        self.ensure_one()
        return self.work_center_assignee_id or super()._verification_officer()

    def _disbursement_act_offered(self, code):
        offered = super()._disbursement_act_offered(code)
        if self.state == "in_progress":
            return offered and self._work_center_offers(code)
        return offered

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
            rec._work_center_enter_circuit(
                "resubmit" if rec.env.context.get("disbursement_resubmit") else "enter"
            )

    def _work_center_enter_circuit(self, act="enter"):
        self.ensure_one()
        # In progress first, so the arrival hooks see the state they expect.
        self.state = "in_progress"
        # sudo: the Saraban head who signs may not read the stations; the
        # signer is still recorded as the mover.
        self.sudo()._work_center_enter(act)

    def action_work_center_enter_circuit(self):
        """Send requests that stayed signed (signed while no route was active,
        or before this module was installed) to the first station."""
        if not self.env.su and not self.env.user.has_group(
            "disbursement.group_disbursement_officer"
        ):
            raise AccessError(
                _("Only a disbursement officer can send requests to the stations.")
            )
        if self.filtered(lambda r: r.state != "signed"):
            raise UserError(_("Only signed requests can be sent to the stations."))
        for rec in self:
            if not rec._work_center_route():
                raise UserError(
                    _("There is no active route for disbursement requests.")
                )
            rec._work_center_enter_circuit()
        return True

    def _work_center_on_exit(self):
        self.state = "done"

    def _disbursement_check_not_returned(self):
        if self.returned_to_source:
            raise UserError(
                _(
                    "This request was returned to its source document. "
                    "Please wait for the correction to be confirmed."
                )
            )

    def _work_center_forward(self, reason=None, expected_station=None):
        self._disbursement_check_not_returned()
        return super()._work_center_forward(reason, expected_station)

    def _work_center_divert(self, station, reason=None, expected_station=None):
        self._disbursement_check_not_returned()
        return super()._work_center_divert(station, reason, expected_station)

    # A DR is sent back only through its own Return wizard: a request whose
    # source can be corrected stays at its station, which the engine's
    # send-back (it leaves the station first) cannot do.
    def action_work_center_send_back(self):
        self.ensure_one()
        self._work_center_check_move()
        return self.action_return_open_wizard()

    def _work_center_send_back(self, reason, expected_station=None):
        self.ensure_one()
        return self._action_return_for_edit(reason)

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

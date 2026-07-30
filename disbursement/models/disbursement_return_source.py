# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

# Generic return/correction To-Do activity types (data/mail_activity_type_data.xml).
# Matched by activity_type_id (language-independent), so resolution works
# regardless of the language an activity was scheduled in.
_ACT_SOURCE_CORRECT = "disbursement.mail_activity_source_correct"
_ACT_SOURCE_DONE = "disbursement.mail_activity_source_done"
_ACT_DR_AWAIT = "disbursement.mail_activity_dr_await"
_ACT_DR_CONTINUE = "disbursement.mail_activity_dr_continue"


def _schedule_todo(record, user, act_xmlid, note=False):
    """Raise a To-Do of the given activity type on ``record`` for ``user``
    (no-op without a user). The activity type's translated name is the title."""
    if user:
        record.activity_schedule(act_xmlid, user_id=user.id, note=note or "")


def _resolve_todos(record, act_xmlid):
    """Auto-resolve (remove) the open activities of ``act_xmlid`` on ``record``."""
    act_type = record.env.ref(act_xmlid)
    record.activity_ids.filtered(
        lambda a: a.activity_type_id == act_type
    ).unlink()


class DisbursementReturnSourceMixin(models.AbstractModel):
    """Contract for a source document that a disbursement request can be
    returned to for correction-in-place.

    When the verification officer returns a signed DR, the DR is kept as-is at
    ``signed`` (no cancel, no budget change) and its source document is bounced
    into a ``returned`` state where a limited set of fields can be corrected.
    Confirming the correction pushes those fields back onto the DR and returns
    the source to its prior state.

    Each concrete source model (approval.request, purchase.order,
    purchase.request.approval, work.acceptance) inherits this mixin, adds a
    ``returned`` state to its own selection, sets ``_disbursement_return_state``
    and implements the hooks below.
    """

    _name = "disbursement.return.source.mixin"
    _description = "Correctable Disbursement Source"

    # State the source sits in while a DR exists; a return cycles
    # _disbursement_return_state -> 'returned' -> _disbursement_return_state.
    _disbursement_return_state = None

    # Staging fields edited while the source is 'returned'; the default
    # _disbursement_apply_correction pushes them onto the DR on confirm. A source
    # with a richer correction surface (e.g. approval.request's per-payee banks)
    # overrides _disbursement_apply_correction and ignores these.
    disbursement_return_note = fields.Text(
        string="Correction Note",
        copy=False,
        help="Corrected description/note pushed onto the disbursement request "
             "when the correction is confirmed.",
    )
    disbursement_return_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Correction Bank Account",
        copy=False,
        help="Corrected payee bank account pushed onto the disbursement request "
             "lines when the correction is confirmed.",
    )

    def _disbursement_return(self, dr, reason):
        """Move this source into ``returned`` for correction. Called (sudo) by
        the DR side when a signed DR is returned by the verification officer."""
        for rec in self:
            if rec.state != rec._disbursement_return_state:
                raise UserError(
                    _("This document cannot be returned in its current state.")
                )
            rec.state = "returned"
        return True

    def action_confirm_correction(self):
        """Requester confirms the correction: push the corrected fields onto the
        still-signed DR and return this source to its prior state."""
        self.ensure_one()
        if self.state != "returned":
            raise UserError(
                _("Only returned documents can confirm a correction.")
            )
        dr = self._disbursement_get_request()
        self.state = self._disbursement_return_state
        if dr:
            dr.sudo()._apply_source_correction(self)
            self.message_post(
                body=_("Correction confirmed; disbursement %s updated.")
                % dr.name
            )
        return True

    # -- hooks each concrete source implements ---------------------------
    def _disbursement_get_request(self):
        """Return the single disbursement.request to push the correction to."""
        raise NotImplementedError

    def _disbursement_pick_request(self, requests):
        """Pick the DR a confirmed correction targets: the one flagged returned,
        else the first non-cancelled. Shared helper for _disbursement_get_request."""
        return requests.filtered(
            lambda d: d.returned_to_source and d.state != "cancel"
        )[:1] or requests.filtered(lambda d: d.state != "cancel")[:1]

    def _disbursement_apply_correction(self, dr):
        """Push this source's corrected fields onto the still-signed ``dr``.

        Default: push the staging note/bank + copy evidence. Sources with a
        richer correction surface override this. The generic banner/To-Do/state
        bookkeeping is handled by the DR side (``_apply_source_correction``)."""
        self.ensure_one()
        if self.disbursement_return_note:
            dr.note = self.disbursement_return_note
        if self.disbursement_return_bank_id:
            dr.line_ids.write(
                {"partner_bank_id": self.disbursement_return_bank_id.id}
            )
        self._disbursement_copy_evidence(dr)

    def _disbursement_correction_user(self):
        """User to notify to perform the correction (the source owner)."""
        self.ensure_one()
        return self.create_uid

    # -- evidence attachments --------------------------------------------
    def _disbursement_evidence_attachments(self):
        """Return the ir.attachment recordset holding correction evidence to
        copy to the DR. Concrete source overrides to point at its own field."""
        return self.env["ir.attachment"].browse()

    def _disbursement_copy_evidence(self, dr):
        """Copy newly-attached evidence onto the DR, skipping any already present
        (matched by checksum) so re-confirming never duplicates files."""
        self.ensure_one()
        existing = set(
            self.env["ir.attachment"].sudo().search([
                ("res_model", "=", "disbursement.request"),
                ("res_id", "=", dr.id),
            ]).mapped("checksum")
        )
        for attachment in self._disbursement_evidence_attachments():
            if attachment.checksum in existing:
                continue
            attachment.sudo().copy({
                "res_model": "disbursement.request",
                "res_id": dr.id,
            })


class DisbursementRequest(models.Model):
    """Generic return-to-source layer on the DR.

    Loaded after ``disbursement_request_assignment`` so the ``_action_return_for_edit``
    dispatcher and the ``action_validate`` guard sit on top of the base
    signed -> draft return-for-correction behaviour in the MRO.
    """

    _inherit = "disbursement.request"

    returned_to_source = fields.Boolean(
        string="Returned to Source",
        copy=False,
        tracking=True,
        help="Set when this request was returned to its source document for "
             "correction: the DR is kept at 'signed' and the source is bounced "
             "to 'returned'. Cleared once the correction is confirmed.",
    )
    return_source_reason = fields.Text(
        string="Return to Source Reason",
        copy=False,
    )

    def _get_return_source(self):
        """Return the source record (a ``disbursement.return.source.mixin``) to
        bounce a return to, or an empty recordset. Bridges override and
        super-chain; the most specific source wins (e.g. WA over PO, which the
        module dependency order guarantees in the MRO)."""
        self.ensure_one()
        return self.env["disbursement.return.source.mixin"]

    def _return_source_officer(self):
        self.ensure_one()
        return self._verification_officer()

    # -- return-for-correction dispatch ----------------------------------
    def _action_return_for_edit(self, reason):
        """Dispatch a return: DRs with a correctable source bounce the source to
        'returned' (DR kept at 'signed'); the rest fall back to the base
        signed -> draft return-for-correction."""
        to_source = self.filtered(lambda d: d._get_return_source())
        for record in to_source:
            record._return_to_source(record._get_return_source(), reason)
        remaining = self - to_source
        if remaining:
            return super()._action_return_for_edit(reason)
        return True

    def _return_to_source(self, source, reason):
        """Bounce ``source`` to 'returned' without touching this DR (kept at
        'signed', no budget change). Records the reason, posts chatter on both
        sides, and raises To-Dos for the requester and the officer."""
        self.ensure_one()
        if self.state != "signed":
            raise UserError(
                _("Only a request under verification (signed) can be returned.")
            )
        self.returned_to_source = True
        self.return_source_reason = reason
        # The officer may not have write access to the source document; sudo the
        # source-side state change, chatter and To-Do.
        source = source.sudo()
        source._disbursement_return(self, reason)
        self.message_post(
            body=_(
                "<p><b>Returned to source for correction</b></p>"
                "<p>This request was returned to its source document "
                "<b>%(source)s</b> by the verification officer. It stays under "
                "verification until the correction is confirmed.<br/>"
                "Reason: <b>%(reason)s</b></p>"
            ) % {"source": source.display_name, "reason": reason},
            subtype_xmlid="mail.mt_comment",
        )
        source.message_post(
            body=_(
                "<p><b>Returned for correction</b></p>"
                "<p>Disbursement <b>%(dr)s</b> was returned by the "
                "verification officer.<br/>Reason: <b>%(reason)s</b><br/>"
                "Please correct the payee bank, description or evidence, then "
                "click <b>Confirm Correction</b>.</p>",
                dr=self.name,
                reason=reason,
            ),
            subtype_xmlid="mail.mt_comment",
        )
        _schedule_todo(
            source, source._disbursement_correction_user(), _ACT_SOURCE_CORRECT, reason
        )
        _schedule_todo(self, self._return_source_officer(), _ACT_DR_AWAIT, reason)
        return True

    def _apply_source_correction(self, source):
        """Pull ``source``'s corrected fields onto this signed DR, clear the
        returned banner, and resolve/raise the return To-Dos on both sides."""
        self.ensure_one()
        source._disbursement_apply_correction(self)
        self.returned_to_source = False
        self.return_source_reason = False
        source_sudo = source.sudo()
        _resolve_todos(self, _ACT_DR_AWAIT)
        _resolve_todos(source_sudo, _ACT_SOURCE_CORRECT)
        _schedule_todo(self, self._return_source_officer(), _ACT_DR_CONTINUE)
        _schedule_todo(
            source_sudo, source._disbursement_correction_user(), _ACT_SOURCE_DONE
        )
        self.message_post(
            body=_(
                "Source correction applied: payee bank, description and "
                "evidence updated. Please continue verification."
            )
        )
        return True

    def action_validate(self):
        """Block validation while a correction is pending on the source side.

        The DR is kept at 'signed' when returned, so without this guard the
        officer could validate/approve (and obligate budget) against the stale
        data before the requester confirms the correction."""
        for record in self:
            if record.returned_to_source:
                raise UserError(
                    _(
                        "This request was returned to its source document. "
                        "Please wait for the correction to be confirmed before "
                        "validating."
                    )
                )
        res = super().action_validate()
        # The officer acted on the correction: auto-resolve the "continue
        # verification" / "correction submitted" To-Dos on both sides.
        for record in self:
            _resolve_todos(record, _ACT_DR_CONTINUE)
            source = record._get_return_source()
            if source:
                _resolve_todos(source.sudo(), _ACT_SOURCE_DONE)
        return res

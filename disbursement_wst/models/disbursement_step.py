# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .disbursement_route import _domain_matches


class DisbursementStep(models.Model):
    """One station visit of one request: who may act, who did, and when.

    Rows are only written by the engine under ``sudo`` — ``act()`` is the single
    gate every transition passes through, so authority is enforced in one place
    no matter how the transition is reached (button, RPC or batch).
    """

    _name = "disbursement.step"
    _description = "Disbursement Step"
    _inherit = ["state.leadtime.mixin"]
    _order = "attempt_seq, sequence, id"

    request_id = fields.Many2one(
        "disbursement.request", required=True, ondelete="cascade", index=True
    )
    station_id = fields.Many2one(
        "disbursement.station", required=True, ondelete="restrict"
    )
    station_code = fields.Char(
        related="station_id.code", store=True, index=True
    )
    sequence = fields.Integer()
    condition_domain = fields.Char(
        help="Copied from the route line when seeded; the step is skipped "
        "on activation if the request no longer matches.",
    )
    state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("active", "Active"),
            ("done", "Done"),
            ("skipped", "Skipped"),
        ],
        default="waiting",
        required=True,
        readonly=True,
        index=True,
    )
    actor_user_ids = fields.Many2many(
        "res.users",
        string="Holders",
        readonly=True,
        help="Members of the station's group when the step was activated.",
    )
    disposition = fields.Selection(
        [("complete", "Complete"), ("return", "Return")], readonly=True
    )
    acted_by_id = fields.Many2one("res.users", readonly=True)
    acted_date = fields.Datetime(readonly=True)
    activated_date = fields.Datetime(readonly=True)
    note = fields.Text(readonly=True)

    # === Signature snapshot (frozen at acting, disbursement ADR-0002) ===
    signed_name = fields.Char(string="Signer Name (snapshot)", readonly=True, copy=False)
    signed_position_name = fields.Char(
        string="Signer Position (snapshot)", readonly=True, copy=False
    )
    signed_signature = fields.Binary(
        string="Signature (snapshot)", attachment=True, readonly=True, copy=False
    )
    signature_image = fields.Binary(
        string="Signature",
        compute="_compute_signature_image",
        help="What the report prints: the snapshot, or the actor's current "
        "employee signature when the snapshot is empty.",
    )

    # A returned round is archived so the PDF prints only the current one while
    # the history stays.
    active = fields.Boolean(default=True)
    attempt_seq = fields.Integer(default=1, index=True)
    can_act = fields.Boolean(compute="_compute_can_act")

    @api.depends("signed_signature", "acted_by_id")
    def _compute_signature_image(self):
        # sudo: whether the official document shows a signature must not depend
        # on the printing user's hr.employee read grants.
        for step in self:
            step.signature_image = (
                step.signed_signature
                or step.acted_by_id.sudo().employee_id.signature
                or False
            )

    @api.depends("state", "station_id.group_id")
    @api.depends_context("uid")
    def _compute_can_act(self):
        groups = self.env.user.groups_id
        for step in self:
            step.can_act = step.state == "active" and step.station_id.group_id in groups

    # ----------------------------------------------------------------- acting
    def _check_act_allowed(self, disposition):
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("This step is not active."))
        if self.station_id.group_id not in self.env.user.groups_id:
            raise AccessError(
                _("You are not authorised to act at station %s.", self.station_id.name)
            )
        if disposition not in ("complete", "return"):
            raise UserError(_("Unknown disposition: %s", disposition))

    def act(self, disposition, vals=None):
        """The single entry point for every transition of a step."""
        self.ensure_one()
        vals = vals or {}
        self._check_act_allowed(disposition)
        # Authority is verified above; the transition itself is a system
        # operation (the actor is recorded in acted_by_id, env.user is kept).
        step = self.sudo()
        request = step.request_id
        if disposition == "complete":
            request._station_check(step.station_code)
            step._stamp("complete", vals.get("note"))
            request._station_complete(step.station_code)
            step._advance()
        else:
            if not vals.get("note"):
                raise UserError(_("A note is required to return a request."))
            request._action_return_to_verification(vals["note"])
        return True

    def _stamp(self, disposition, note):
        self.ensure_one()
        user = self.env.user
        vals = {
            "state": "done",
            "disposition": disposition,
            "acted_by_id": user.id,
            "acted_date": fields.Datetime.now(),
            "note": note,
        }
        if disposition == "complete" and self.station_id.is_signature:
            employee = user.sudo().employee_id
            vals.update(
                signed_name=employee.name or user.name,
                signed_position_name=employee.job_title or "",
                signed_signature=employee.signature or False,
            )
        self.write(vals)
        self._clear_activities()

    def _advance(self):
        """Activate the next step that applies, or finish the route."""
        self.ensure_one()
        request = self.request_id
        for step in request.step_ids.filtered(
            lambda s: s.state == "waiting" and s.attempt_seq == self.attempt_seq
        ).sorted(lambda s: (s.sequence, s.id)):
            if _domain_matches(step.condition_domain, request):
                step._activate()
                return
            step.state = "skipped"
        request._finish_route()

    def _activate(self):
        self.ensure_one()
        self.write(
            {
                "state": "active",
                "activated_date": fields.Datetime.now(),
                "actor_user_ids": [(6, 0, self.station_id.group_id.users.ids)],
            }
        )
        self.request_id._station_enter(self.station_code)
        self._notify_holders()

    # ------------------------------------------------------------------- todos
    def _notify_holders(self):
        """Push the station's Todo to every holder of the step."""
        for step in self:
            activity_type = step.station_id.activity_type_id
            if not activity_type:
                continue
            for user in step.actor_user_ids:
                step.request_id.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    note=step.request_id.name or "",
                )

    def _clear_activities(self):
        """Drop the station's Todos on the request, for all holders."""
        for step in self:
            activity_type = step.station_id.activity_type_id
            if activity_type:
                step.request_id.activity_ids.filtered(
                    lambda a, t=activity_type: a.activity_type_id == t
                ).unlink()

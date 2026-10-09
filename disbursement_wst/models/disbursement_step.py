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
    _order = "sequence, id"

    request_id = fields.Many2one(
        "disbursement.request", required=True, ondelete="cascade", index=True
    )
    # The step carries its own frozen copy of what it needs from the station
    # (ADR-0005), so the journey survives the station module being uninstalled:
    # ``station_id`` is nulled then, the copies are not.
    station_id = fields.Many2one("disbursement.station", ondelete="set null")
    station_code = fields.Char(index=True, readonly=True)
    station_name = fields.Char(readonly=True)
    is_signature = fields.Boolean(readonly=True)
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
    # How the step ended. Kept apart on purpose: counting diverts is how you find
    # out which station keeps sending work back.
    disposition = fields.Selection(
        [("forward", "Forward"), ("divert", "Divert")], readonly=True
    )
    # Where the step came from: the route, a divert (detour), or the diverting
    # station queued again behind the detour.
    origin = fields.Selection(
        [("route", "Route"), ("insert", "Inserted"), ("resume", "Resumed")],
        default="route",
        required=True,
        readonly=True,
    )
    inserted_by_step_id = fields.Many2one(
        "disbursement.step", string="Caused By", readonly=True, ondelete="set null"
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

    can_act = fields.Boolean(compute="_compute_can_act")

    @api.model_create_multi
    def create(self, vals_list):
        Station = self.env["disbursement.station"]
        for vals in vals_list:
            station = Station.browse(vals.get("station_id"))
            vals.setdefault("station_code", station.code)
            vals.setdefault("station_name", station.name)
            vals.setdefault("is_signature", station.is_signature)
        return super().create(vals_list)

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
    def _check_act_allowed(self):
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("This step is not active."))
        if self.station_id.group_id not in self.env.user.groups_id:
            raise AccessError(
                _("You are not authorised to act at station %s.", self.station_id.name)
            )

    def act(self, note=None):
        """The single entry point for every transition of a step."""
        self.ensure_one()
        self._check_act_allowed()
        # Authority is verified above; the transition itself is a system
        # operation (the actor is recorded in acted_by_id, env.user is kept).
        self.sudo()._do_complete(note)
        return True

    def divert(self, station, come_back=True, note=None):
        """Say something is wrong here: send the request to ``station``.

        The route is unchanged underneath. The detour is two creates and a
        renumbering: ``station`` is inserted right after this step, and with
        ``come_back`` this station is queued again behind it, so the request
        runs ``X -> Y -> X -> (route continues)`` rather than
        ``X -> Y -> (route continues)``.
        """
        self.ensure_one()
        self._check_act_allowed()
        if not note:
            raise UserError(_("A note is required to divert a request."))
        if station == self.station_id:
            raise UserError(_("A request cannot be diverted to the station it is at."))
        self.request_id._check_divert_target(station)
        self.sudo()._do_divert(station, come_back, note)
        return True

    def _do_complete(self, note=None):
        """Complete the step without the group check.

        ``act()`` is the gate for a person pressing a button. A station whose
        completion is a business event (a bill posted, a payment booked) calls
        this directly from that event: the event's own workflow is the authority.
        """
        self.ensure_one()
        request = self.request_id
        request._station_check(self.station_code)
        self._stamp("forward", note)
        request._station_complete(self.station_code)
        self._advance()

    def _do_divert(self, station, come_back, note):
        self.ensure_one()
        self._stamp("divert", note)
        self._open_slots(2 if come_back else 1)
        detour = self._copy_for(station, self.sequence + 1, "insert")
        if come_back:
            self._copy_for(self.station_id, self.sequence + 2, "resume")
        self._advance()
        return detour

    def _open_slots(self, count):
        """Renumber the steps still waiting so ``count`` slots follow this one.

        Renumbered rather than shifted: route lines may share a sequence, and a
        shifted step tied with the inserted one would sort by id, ahead of it.
        """
        waiting = self.request_id.step_ids.filtered(
            lambda s: s.state == "waiting"
        ).sorted(lambda s: (s.sequence, s.id))
        for offset, step in enumerate(waiting, start=count + 1):
            step.sequence = self.sequence + offset

    def _copy_for(self, station, sequence, origin):
        """A step of the same request at ``station``, caused by this one."""
        return self.create(
            {
                "request_id": self.request_id.id,
                "station_id": station.id,
                "sequence": sequence,
                "origin": origin,
                "inserted_by_step_id": self.id,
            }
        )

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
        if disposition == "forward" and self.is_signature:
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
            lambda s: s.state == "waiting"
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

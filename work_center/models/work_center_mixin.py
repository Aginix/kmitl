from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import plaintext2html

ARRIVAL_ACTIVITY = "work_center.mail_activity_station_arrival"


class WorkCenterMixin(models.AbstractModel):
    """Puts a document at a สถานี (station) and moves it along its route
    (ADR-0002).

    * ``work_center_id`` is the pointer to the station holding the document.
      Only ``_work_center_move`` writes it, so every change is in the visit log
      (สมุดเยี่ยม). The standard route is configuration, read live.
    * ``_work_center_forward`` hands the document to the next station,
      ``_work_center_divert`` to another station of the same area,
      ``_work_center_leave`` takes it out of the circuit.
    * Which acts a station offers, and who may press them, is decided here
      from the act registry: the role gives the right, membership only narrows.

    Consumers inherit the mixin with an explicit ``_name`` next to
    ``mail.thread`` (tracking) and ``mail.activity.mixin`` (arrival Todos),
    declare their acts in ``_work_center_acts`` and implement the hooks.
    """

    _name = "work.center.mixin"
    _description = "Station Mixin"
    _work_center_ou_field = "operating_unit_id"

    work_center_id = fields.Many2one(
        comodel_name="work.center",
        string="Station",
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
        ondelete="restrict",
        help="The station holding the document. It only changes through the "
        "forward, divert, send back and exit actions.",
    )
    work_center_visit_ids = fields.One2many(
        comodel_name="work.center.visit",
        inverse_name="res_id",
        string="Visit Log",
        readonly=True,
    )
    work_center_open_visit_id = fields.Many2one(
        comodel_name="work.center.visit",
        string="Current Visit",
        compute="_compute_work_center_state",
    )
    work_center_next_id = fields.Many2one(
        comodel_name="work.center",
        string="Next Station",
        compute="_compute_work_center_state",
        help="Where forwarding would send the document now, on the live route.",
    )
    work_center_missing_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        string="Acts Still to Do",
        compute="_compute_work_center_state",
        help="Required at this station and not yet done in this visit.",
    )
    work_center_can_move = fields.Boolean(
        string="Can Move",
        compute="_compute_work_center_state",
        help="Technical: the current user may forward, divert or send back.",
    )

    @api.model
    def _valid_field_parameter(self, field, name):
        # ``tracking`` is only meaningful once a consumer adds mail.thread.
        return name == "tracking" or super()._valid_field_parameter(field, name)

    @api.constrains("work_center_id")
    def _check_work_center_id(self):
        if self.filtered("work_center_id.is_unassigned"):
            raise ValidationError(_("A document cannot be put on the Unassigned card."))

    # ------------------------------------------------------------------
    # Hooks for the consumer (defaults do nothing)
    # ------------------------------------------------------------------
    @api.model
    def _work_center_acts(self):
        """Declare the acts and editable parts of this document model, as a
        list of dicts ``{code, name (lazy), kind, group (xmlid), sequence,
        module}``. Extend with ``super()``; the registry reflects them."""
        return []

    def _work_center_act_applies(self, code):
        """Whether an act concerns this document at all. A required act that
        does not is not missing; the visit logs it as not applicable."""
        return True

    @api.model
    def _work_center_circuit_domain(self):
        """The documents that are in the circuit. The Unassigned card counts
        only these among the documents no station holds."""
        return []

    def _work_center_on_arrival(self, visit):
        """The document has just arrived at ``visit.work_center_id``."""

    def _work_center_on_departure(self, visit):
        """The document has just left the station of ``visit`` (closed)."""

    def _work_center_on_exit(self):
        """The document left the last station of the route."""

    def _work_center_on_send_back(self, reason):
        """The document was sent back to its maker."""

    # ------------------------------------------------------------------
    # Where the document is
    # ------------------------------------------------------------------
    def _work_center_open_visit(self):
        self.ensure_one()
        Visit = self.env["work.center.visit"].sudo()
        if not isinstance(self.id, int):
            return Visit
        return Visit.search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("departure_date", "=", False),
            ],
            order="id desc",
            limit=1,
        )

    def _work_center_holding_station(self):
        """The station holding the document: the pointer, or — when the pointer
        is empty and a visit is open — that visit's station (the Unassigned
        card after a placement no rule resolved). Every authority and divert
        check reads this, never the raw pointer. Returned as sudo."""
        self.ensure_one()
        if self.work_center_id:
            return self.sudo().work_center_id
        return self._work_center_open_visit().work_center_id

    def _work_center_route(self):
        """The active route of this document model (one with lines)."""
        self.ensure_one()
        return (
            self.env["work.center.route"]
            .sudo()
            .search(
                [
                    ("model_id", "=", self.env["ir.model"]._get_id(self._name)),
                    ("line_ids", "!=", False),
                ],
                limit=1,
            )
        )

    def _work_center_ou_compatible(self, stations):
        field = self._work_center_ou_field
        if field not in self._fields:
            return stations
        unit = self[field]
        return stations.filtered(
            lambda station: not station.operating_unit_id
            or station.operating_unit_id == unit
        )

    def _work_center_resolve(self, line):
        """The station of a route line that takes this document: the only
        candidate, or the one the routing rules pick. Empty when none does."""
        self.ensure_one()
        candidates = self._work_center_ou_compatible(
            line.sudo().work_center_ids.filtered(
                lambda station: station.active and not station.is_unassigned
            )
        )
        if len(candidates) <= 1:
            return candidates
        Rule = self.env["work.center.rule"].sudo()
        rules = Rule._candidate_rules(self._name).filtered(
            lambda rule: rule.work_center_id in candidates
        )
        return Rule._match(self.sudo(), rules)

    def _work_center_next_line(self):
        """The route line after the last on-route station the document visited
        in this round (by visit id), or ``None`` after the last line. A document
        that has not visited the route yet is due at line 1."""
        self.ensure_one()
        lines = self._work_center_route().line_ids
        visits = self.env["work.center.visit"].sudo().search(
            [("res_model", "=", self._name), ("res_id", "=", self.id)],
            order="id desc",
        )
        for visit in visits:
            for index, line in enumerate(lines):
                if visit.work_center_id in line.work_center_ids:
                    return lines[index + 1] if index + 1 < len(lines) else None
            if visit.arrival_act in ("enter", "resubmit"):
                break  # the visits before belong to an earlier round
        return lines[:1] or None

    def _work_center_unassigned_card(self):
        area = (
            self.env["work.center.area"]
            .sudo()
            .search([("model_ids.model", "=", self._name)], limit=1)
        )
        if not area:
            raise UserError(_("No work area covers %s.") % self._description)
        return area.unassigned_work_center_id

    # ------------------------------------------------------------------
    # Acts and authority
    # ------------------------------------------------------------------
    @api.model
    def _work_center_live_codes(self):
        """The codes the code declares right now. Computed from the code, not
        read from the registry, so an uninstall (which skips the sync) cannot
        leave a phantom act that blocks a document."""
        return {declaration["code"] for declaration in self._work_center_acts()}

    def _work_center_station_act(self, code):
        """The act or editable part ``code`` among what the holding station
        lists, or an empty recordset."""
        station = self._work_center_holding_station()
        return (station.allowed_act_ids | station.allowed_edit_ids).filtered(
            lambda act: act.code == code
        )[:1]

    def _work_center_find_act(self, code):
        """The act the holding station lists for ``code``. Only the pilot
        snippet sets ``work_center_act_anywhere`` to look past the station, to
        place a legacy document."""
        if self.env.su and self.env.context.get("work_center_act_anywhere"):
            return (
                self.env["work.center.act"]
                .sudo()
                .with_context(active_test=False)
                .search([("code", "=", code)], limit=1)
            )
        return self._work_center_station_act(code)

    def _work_center_station_members(self):
        station = self._work_center_holding_station()
        return station._active_members() if station else self.env["res.users"]

    def _work_center_user_may_act(self, user, act):
        """The role gives the right and membership narrows it: the user holds
        the act's role, and the station has no members or lists the user."""
        self.ensure_one()
        if not act.group_id or act.group_id not in user.sudo().groups_id:
            return False
        members = self._work_center_station_members()
        return not members or user in members

    def _work_center_offers(self, code):
        """Whether the act (or editable part) is offered to the current user
        on this document now. The role and membership halves are bypassed
        under su; "the station allows it" never is, unless the pilot snippet
        sets ``work_center_act_anywhere``."""
        self.ensure_one()
        if code not in self._work_center_live_codes():
            return False
        if not self._work_center_act_applies(code):
            return False
        act = self._work_center_find_act(code)
        if not act or not act.active:
            return False
        return bool(self.env.su or self._work_center_user_may_act(self.env.user, act))

    def _work_center_check_act(self, code):
        """Raise unless the current user may perform the act here and now."""
        self.ensure_one()
        act = self._work_center_find_act(code)
        if not act or not act.active or code not in self._work_center_live_codes():
            raise UserError(
                _("This act is not allowed at the station holding this document.")
            )
        if self.env.su:
            return
        user = self.env.user
        if not act.group_id or act.group_id not in user.sudo().groups_id:
            raise AccessError(_("You do not hold the role this act requires."))
        members = self._work_center_station_members()
        if members and user not in members:
            raise AccessError(
                _("Only the members of the station holding this document can do this.")
            )

    def _work_center_act_done(self, code):
        """Record the act in the open visit (the evidence that it was done
        here, which forwarding checks against the required acts)."""
        self.ensure_one()
        visit = self._work_center_open_visit()
        if not visit:
            return
        act = (
            self.env["work.center.act"]
            .sudo()
            .with_context(active_test=False)
            .search([("code", "=", code), ("kind", "=", "act")], limit=1)
        )
        if act and act not in visit.done_act_ids:
            visit.with_context(work_center_moving=True).write(
                {"done_act_ids": [(4, act.id)]}
            )

    def _work_center_act_status(self, visit, station):
        """(missing, not applicable): the live, grouped, required acts of the
        station, minus those done in this visit; those the document declared
        not applicable to itself are set apart rather than missing."""
        live = self._work_center_live_codes()
        required = station.sudo().required_act_ids.filtered(
            lambda act: act.active and act.group_id and act.code in live
        )
        pending = required - visit.done_act_ids
        not_applicable = pending.filtered(
            lambda act: not self._work_center_act_applies(act.code)
        )
        return pending - not_applicable, not_applicable

    def _work_center_user_may_move(self, user):
        """Forward, divert and send back are for the people responsible at the
        station: its members; else the holders of its acts' roles; else — only
        when nobody is left — the station administrators. There is no manager
        override where somebody is responsible (D14)."""
        self.ensure_one()
        if self.env.su:
            return True
        station = self._work_center_holding_station()
        if not station:
            return False
        users, _source = station._responsible_users()
        return user in users

    def _work_center_check_move(self):
        self.ensure_one()
        if not self._work_center_user_may_move(self.env.user):
            raise AccessError(
                _("Only the people responsible at the station holding this "
                  "document can move it.")
            )

    def _work_center_last_visit(self, departure_acts=("forward", "exit")):
        """The latest closed visit that ended with one of ``departure_acts``."""
        self.ensure_one()
        return (
            self.env["work.center.visit"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("departure_act", "in", list(departure_acts)),
                ],
                order="id desc",
                limit=1,
            )
        )

    @api.depends(
        "work_center_id",
        "work_center_visit_ids.departure_date",
        "work_center_visit_ids.done_act_ids",
    )
    @api.depends_context("uid")
    def _compute_work_center_state(self):
        for rec in self:
            visit = rec._work_center_open_visit()
            station = (
                rec._work_center_holding_station()
                if visit or rec.work_center_id
                else None
            )
            rec.work_center_open_visit_id = visit
            rec.work_center_can_move = bool(station) and rec._work_center_user_may_move(
                self.env.user
            )
            missing = self.env["work.center.act"]
            following = self.env["work.center"]
            if visit and station and not station.is_unassigned:
                missing = rec._work_center_act_status(visit, station)[0]
                line = rec._work_center_next_line()
                following = rec._work_center_resolve(line) if line else following
            rec.work_center_missing_act_ids = missing
            rec.work_center_next_id = following

    # ------------------------------------------------------------------
    # The one writer
    # ------------------------------------------------------------------
    def _work_center_move(
        self,
        station,
        arrival_act,
        departure_act,
        reason=None,
        skipped=None,
        not_applicable=None,
        expected_station=None,
    ):
        """Close the open visit, move the pointer and open the next visit.

        ``station`` is where the document goes: empty with an ``arrival_act``
        puts it on the area's Unassigned card (no rule resolved a station);
        empty without one takes it out of the circuit. Every other move goes
        through here, so the pointer and the visit log cannot disagree.
        """
        self.ensure_one()
        holding = self._work_center_holding_station()
        expected_id = (
            expected_station.id
            if isinstance(expected_station, models.BaseModel)
            else expected_station
        )
        if expected_id and expected_id != holding.id:
            raise UserError(
                _("The document has already moved to another station. Reload and "
                  "try again.")
            )
        visit = self._work_center_open_visit()
        if visit and not departure_act:
            raise UserError(_("The document is already at a station."))
        if not visit and not arrival_act:
            return False  # leaving twice is a no-op
        record = self.sudo()

        # 2. Close the open visit.
        if visit:
            visit.with_context(work_center_moving=True).write(
                {
                    "departure_date": fields.Datetime.now(),
                    "departed_by_id": self.env.user.id,
                    "departure_act": departure_act,
                    "departure_reason": reason or False,
                    "skipped_act_ids": [(6, 0, (skipped or self.env["work.center.act"]).ids)],
                    "not_applicable_act_ids": [
                        (6, 0, (not_applicable or self.env["work.center.act"]).ids)
                    ],
                }
            )
        # 3. The mover's own arrival Todo is done; everyone else's is withdrawn.
        record._work_center_close_arrival_todos(self.env.user)
        # 4. The pointer.
        target = station if arrival_act else self.env["work.center"]
        record.with_context(work_center_moving=True).write(
            {"work_center_id": target.id or False}
        )
        # 5. The next visit, with who is responsible frozen at arrival.
        new_visit = self.env["work.center.visit"]
        if arrival_act:
            placed = station.sudo() or self._work_center_unassigned_card()
            users, source = placed._responsible_users()
            new_visit = (
                self.env["work.center.visit"]
                .sudo()
                .create(
                    {
                        "res_model": self._name,
                        "res_id": self.id,
                        "work_center_id": placed.id,
                        "arrival_act": arrival_act,
                        "arrived_by_id": self.env.user.id,
                        "responsible_user_ids": [(6, 0, users.ids)],
                        "responsible_source": source,
                    }
                )
            )
            # 6. One Todo per responsible user.
            if "activity_ids" in self._fields:
                for user in users:
                    record.activity_schedule(
                        ARRIVAL_ACTIVITY, user_id=user.id, note=self.display_name
                    )
        if reason and "message_ids" in self._fields:
            record.message_post(
                body=Markup("<p><b>%s</b></p>%s")
                % (self._work_center_move_label(arrival_act, departure_act),
                   plaintext2html(reason)),
                subtype_xmlid="mail.mt_note",
            )
        # 7. Hooks, as sudo: the move itself is already authorised.
        if visit:
            record._work_center_on_departure(visit)
        if new_visit:
            record._work_center_on_arrival(new_visit)
        if departure_act == "exit":
            record._work_center_on_exit()
        return True

    def _work_center_move_label(self, arrival_act, departure_act):
        if departure_act == "divert":
            return _("Diverted")
        if departure_act == "send_back":
            return _("Sent back")
        return _("Forwarded")

    def _work_center_close_arrival_todos(self, mover):
        """Mark the mover's own arrival Todo done and withdraw the others
        (never feed back the whole fan-out as one person)."""
        if "activity_ids" not in self._fields:
            return
        arrival = self.env.ref(ARRIVAL_ACTIVITY)
        todos = self.sudo().activity_ids.filtered(
            lambda activity: activity.activity_type_id == arrival
        )
        mine = todos.filtered(lambda activity: activity.user_id == mover)
        (todos - mine).unlink()
        # Still the mover's note (the uid is unchanged under sudo), but a mover
        # with no mail address must not be able to block the move.
        mine.action_feedback()

    # ------------------------------------------------------------------
    # The moves
    # ------------------------------------------------------------------
    def _work_center_enter(self, act="enter"):
        """Enter the circuit at the first station of the route, whatever the
        history is: a corrected document is checked again from the start."""
        self.ensure_one()
        route = self._work_center_route()
        if not route:
            raise UserError(_("There is no standard route for this document."))
        station = self._work_center_resolve(route.line_ids[0])
        self._work_center_move(station, arrival_act=act, departure_act=None)

    def _work_center_forward(self, reason=None, expected_station=None):
        """Hand the document to the next station on the route; out of the last
        one it leaves the circuit (``exit``). Forwarding without a required act
        needs a reason, which is logged with the acts skipped."""
        self.ensure_one()
        station = self._work_center_holding_station()
        if not station or station.is_unassigned:
            raise UserError(_("Divert the document to a station first."))
        self._work_center_check_move()
        if not self._work_center_route():
            raise UserError(_("There is no standard route for this document."))
        missing, not_applicable = self._work_center_act_status(
            self._work_center_open_visit(), station
        )
        reason = (reason or "").strip()
        if missing and not reason:
            raise UserError(
                _("Give a reason to forward without: %s")
                % ", ".join(missing.mapped("name"))
            )
        line = self._work_center_next_line()
        self._work_center_move(
            self._work_center_resolve(line) if line else self.env["work.center"],
            arrival_act="forward" if line else None,
            departure_act="forward" if line else "exit",
            reason=reason or None,
            skipped=missing,
            not_applicable=not_applicable,
            expected_station=expected_station,
        )

    def _work_center_divert_targets(self):
        """The stations the holding station may divert the document to."""
        self.ensure_one()
        holding = self._work_center_holding_station()
        stations = self.env["work.center"].sudo().search(
            [
                ("area_id", "=", holding.area_id.id),
                ("is_unassigned", "=", False),
                ("id", "!=", holding.id),
            ]
        )
        return self._work_center_ou_compatible(stations)

    def _work_center_divert(self, station, reason=None, expected_station=None):
        """Hand the document to any other station of the same area, ignoring
        the required acts. A reason is mandatory."""
        self.ensure_one()
        if not self._work_center_holding_station():
            raise UserError(_("This document is not at a station."))
        self._work_center_check_move()
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Give a reason to divert the document."))
        if station.sudo() not in self._work_center_divert_targets():
            raise UserError(
                _("A document can only be diverted to another station of its own "
                  "work area.")
            )
        self._work_center_move(
            station.sudo(),
            arrival_act="divert",
            departure_act="divert",
            reason=reason,
            expected_station=expected_station,
        )

    def _work_center_leave(self, act, reason=None, expected_station=None):
        """Take the document out of the circuit (``send_back`` or ``cancel``).
        Closes the visit and the Todos and clears the pointer; idempotent when
        no visit is open."""
        self.ensure_one()
        return self._work_center_move(
            self.env["work.center"],
            arrival_act=None,
            departure_act=act,
            reason=reason,
            expected_station=expected_station,
        )

    def _work_center_send_back(self, reason, expected_station=None):
        """Send the document back to its maker; the consumer's
        ``_work_center_on_send_back`` makes it a draft again."""
        self.ensure_one()
        if not self._work_center_holding_station():
            raise UserError(_("This document is not at a station."))
        self._work_center_check_move()
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Give a reason to send the document back."))
        self._work_center_leave("send_back", reason, expected_station)
        self.sudo()._work_center_on_send_back(reason)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def _work_center_wizard_action(self, mode):
        self.ensure_one()
        names = {
            "forward": _("Forward"),
            "divert": _("Divert"),
            "send_back": _("Send Back"),
        }
        return {
            "type": "ir.actions.act_window",
            "name": names[mode],
            "res_model": "work.center.move.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "default_mode": mode,
                "default_expected_station_id": self.env.context.get("expected_station")
                or False,
            },
        }

    def action_work_center_forward(self):
        """Forward straight away when nothing is missing; otherwise ask for
        the reason first."""
        self.ensure_one()
        self._work_center_check_move()
        station = self._work_center_holding_station()
        missing = (
            self._work_center_act_status(self._work_center_open_visit(), station)[0]
            if station and not station.is_unassigned
            else False
        )
        if missing:
            return self._work_center_wizard_action("forward")
        self._work_center_forward(
            expected_station=self.env.context.get("expected_station")
        )
        return True

    def action_work_center_divert(self):
        self.ensure_one()
        self._work_center_check_move()
        return self._work_center_wizard_action("divert")

    def action_work_center_send_back(self):
        self.ensure_one()
        self._work_center_check_move()
        return self._work_center_wizard_action("send_back")

    # ------------------------------------------------------------------
    # Only the engine moves a document
    # ------------------------------------------------------------------
    def _work_center_engine_moving(self):
        """The engine is writing the pointer. The context key alone is not
        trusted: an RPC caller can send any context, and only the engine (which
        writes as sudo) may move a document."""
        return self.env.su and bool(self.env.context.get("work_center_moving"))

    @api.model_create_multi
    def create(self, vals_list):
        if not self._work_center_engine_moving() and any(
            vals.get("work_center_id") for vals in vals_list
        ):
            raise UserError(
                _("A document is put at a station by the station engine, not by hand.")
            )
        return super().create(vals_list)

    def write(self, vals):
        if "work_center_id" in vals and not self._work_center_engine_moving():
            target = vals["work_center_id"] or False
            if any((rec.work_center_id.id or False) != target for rec in self):
                raise UserError(
                    _("A document is moved between stations by the station engine, "
                      "not by hand.")
                )
        return super().write(vals)

    def unlink(self):
        visits = self.env["work.center.visit"].sudo().search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )
        res = super().unlink()
        visits.with_context(work_center_force_unlink=True).unlink()
        return res

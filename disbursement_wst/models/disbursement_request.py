# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    route_id = fields.Many2one(
        "disbursement.route", string="Route", readonly=True, copy=False
    )
    step_ids = fields.One2many(
        "disbursement.step", "request_id", string="Steps", readonly=True, copy=False
    )
    current_step_id = fields.Many2one(
        "disbursement.step",
        compute="_compute_current_step_id",
        store=True,
        index=True,
    )
    # The stations are data: the selection lists whichever station modules are
    # installed, so the status bar grows with them without touching any view.
    station_code = fields.Selection(
        selection="_selection_station_code",
        string="Station",
        compute="_compute_current_step_id",
        store=True,
        index=True,
    )
    current_station_id = fields.Many2one(
        "disbursement.station", related="current_step_id.station_id"
    )
    current_holder_ids = fields.Many2many(
        "res.users", related="current_step_id.actor_user_ids"
    )
    can_act = fields.Boolean(compute="_compute_can_act")
    signature_step_ids = fields.Many2many(
        "disbursement.step", compute="_compute_signature_step_ids"
    )
    # Not stored and not meant to be read: they exist to be *searched*. Odoo 16
    # has no ``any`` operator, so "a done step at this station" cannot be written
    # on ``step_ids`` without matching two different steps.
    done_station_codes = fields.Char(
        compute="_compute_done_station_codes",
        search="_search_done_station_codes",
        help="Search with ``=`` and a station code: requests that completed it.",
    )
    my_done_station_codes = fields.Char(
        compute="_compute_done_station_codes",
        search="_search_my_done_station_codes",
        help="Same, restricted to the steps the current user acted on.",
    )

    @api.model
    def _selection_station_code(self):
        return [
            (station.code, station.name)
            for station in self.env["disbursement.station"].search([])
        ]

    @api.depends("current_step_id.station_id.group_id")
    @api.depends_context("uid")
    def _compute_can_act(self):
        groups = self.env.user.groups_id
        for request in self:
            request.can_act = (
                request.current_step_id.station_id.group_id in groups
                if request.current_step_id
                else False
            )

    @api.depends("step_ids.state")
    def _compute_current_step_id(self):
        for request in self:
            step = request.step_ids.filtered(lambda s: s.state == "active")[:1]
            request.current_step_id = step
            request.station_code = step.station_code

    @api.depends("step_ids.state", "step_ids.disposition", "step_ids.is_signature")
    def _compute_signature_step_ids(self):
        """The latest signing step of each station: a request that detoured can
        visit a station twice, and the officer signs the document once."""
        for request in self:
            latest = {}
            for step in request.step_ids.filtered(
                lambda s: s.state == "done"
                and s.disposition == "forward"
                and s.is_signature
            ).sorted(lambda s: (s.sequence, s.id)):
                latest[step.station_code] = step
            request.signature_step_ids = request.step_ids.browse(
                [step.id for step in latest.values()]
            ).sorted(lambda s: (s.sequence, s.id))

    def _compute_done_station_codes(self):
        self.done_station_codes = self.my_done_station_codes = False

    def _search_done_station_codes(self, operator, value, user=None):
        domain = [("station_code", operator, value), ("state", "=", "done")]
        if user:
            domain.append(("acted_by_id", "=", user))
        steps = self.env["disbursement.step"].sudo().search(domain)
        return [("id", "in", steps.request_id.ids)]

    def _search_my_done_station_codes(self, operator, value):
        return self._search_done_station_codes(operator, value, user=self.env.uid)

    # ----------------------------------------------------------------- route
    def action_sign(self):
        """The head's signature hands the request over to the first station."""
        res = super().action_sign()
        self._start_route()
        return res

    def _start_route(self):
        """Seed the matching route onto the request and enter its first station.

        A request no route can carry stays ``signed``: nobody would pick it up.
        """
        for request in self.sudo():
            route = self.env["disbursement.route"]._find_for(request)
            if not route.line_ids:
                request.message_post(
                    body=_("No route with stations matches this request."),
                    subtype_xmlid="mail.mt_note",
                )
                continue
            request.route_id = route
            request.state = "in_progress"
            request._seed_steps()

    def _reset_route(self):
        """Drop the route (cancel / back to draft): clear its Todos and steps.

        The steps are deleted rather than archived: a reset starts the journey
        over, and what happened is already in the chatter.
        """
        for request in self.sudo().filtered("step_ids"):
            request.step_ids._clear_activities()
            request.step_ids.unlink()
            request.route_id = False

    def _seed_steps(self):
        self.ensure_one()
        steps = self.env["disbursement.step"].create(
            [
                {
                    "request_id": self.id,
                    "station_id": line.station_id.id,
                    "sequence": line.sequence,
                    "condition_domain": line.condition_domain,
                }
                for line in self.route_id.line_ids
            ]
        )
        steps[:1]._advance()

    def _finish_route(self):
        """The last step is done."""
        self.state = "done"

    def action_draft(self):
        res = super().action_draft()
        self._reset_route()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._reset_route()
        return res

    # --------------------------------------------------------------- actions
    def action_station_complete(self):
        """Proceed: complete the current station's step."""
        for request in self:
            request.current_step_id.act()
        return True

    def action_divert(self):
        """Open the divert wizard: name the station that must look at this."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Divert"),
            "res_model": "disbursement.divert.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _check_divert_target(self, station):
        """Refuse a station whose prerequisites this request has not finished.

        Only the stations on this request's own route count: a required station
        that is not on it imposes nothing (ADR-0002).
        """
        self.ensure_one()
        on_route = set(self.step_ids.mapped("station_code"))
        forwarded = set(
            self.step_ids.filtered(
                lambda s: s.state == "skipped"
                or (s.state == "done" and s.disposition == "forward")
            ).mapped("station_code")
        )
        missing = [
            code
            for code in station._required_codes()
            if code in on_route and code not in forwarded
        ]
        if missing:
            raise UserError(
                _(
                    "Station %(station)s needs %(required)s to be done first.",
                    station=station.name,
                    required=", ".join(
                        sorted(
                            {
                                step.station_name
                                for step in self.step_ids
                                if step.station_code in missing
                            }
                        )
                    ),
                )
            )

    def action_act_batch(self):
        """Proceed many requests at once from a work queue."""
        return self._run_batch("action_station_complete")

    def _run_batch(self, method):
        """Run ``method`` on each request in its own savepoint.

        One that fails (e.g. insufficient budget) does not roll back the rest;
        returns a summary notification.
        """
        done = self.browse()
        failures = []
        for record in self:
            try:
                with self.env.cr.savepoint():
                    getattr(record, method)()
                done |= record
            except (UserError, ValidationError) as error:
                self.env.invalidate_all()
                failures.append(
                    (record.display_name, error.args and error.args[0] or _("error"))
                )
        message = _("%s request(s) processed.") % len(done)
        if failures:
            message += "\n" + _("Could not process:") + "\n"
            message += "\n".join("• %s — %s" % (name, why) for name, why in failures)
        if failures and not done:
            notification_type = "danger"
        elif failures:
            notification_type = "warning"
        else:
            notification_type = "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Work Station"),
                "message": message,
                "type": notification_type,
                "sticky": bool(failures),
            },
        }

    def _wst_check_station_removable(self, code):
        """Refuse to uninstall station ``code`` while a request is parked at it.

        Called from each station module's ``uninstall_hook`` (ADR-0005): history
        survives the station, work in progress does not.
        """
        parked = self.search([("station_code", "=", code)])
        if parked:
            raise UserError(
                _(
                    "Cannot remove this work station: %(count)s request(s) are "
                    "waiting at it: %(names)s. Send them on first.",
                    count=len(parked),
                    names=", ".join(parked.mapped("name")),
                )
            )

    # ---------------------------------------------------------------- hooks
    def _station_check(self, code):
        """Raise UserError if the station ``code`` cannot be completed yet."""

    def _station_enter(self, code):
        """Side effect on entering the station ``code``."""

    def _station_complete(self, code):
        """Side effect on completing the station ``code``."""

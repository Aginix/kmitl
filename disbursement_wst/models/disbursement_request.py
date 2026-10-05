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
    attempt_seq = fields.Integer(default=1, copy=False)
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

    @api.depends("step_ids.state", "step_ids.active")
    def _compute_current_step_id(self):
        for request in self:
            step = request.step_ids.filtered(lambda s: s.state == "active")[:1]
            request.current_step_id = step
            request.station_code = step.station_code

    @api.depends("step_ids.state", "step_ids.disposition", "step_ids.station_id.is_signature")
    def _compute_signature_step_ids(self):
        for request in self:
            request.signature_step_ids = request.step_ids.filtered(
                lambda s: s.state == "done"
                and s.disposition == "complete"
                and s.station_id.is_signature
            )

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

    def _restart_route(self, reason=None):
        """Return: archive the current round and walk the route again."""
        for request in self.sudo():
            if request.current_step_id:
                request.current_step_id._stamp("return", reason)
            request.step_ids.write({"active": False})
            request.attempt_seq += 1
            request._seed_steps()

    def _reset_route(self):
        """Drop the route (cancel / back to draft): clear its Todos, archive it."""
        for request in self.sudo().filtered("step_ids"):
            request.step_ids._clear_activities()
            request.step_ids.write({"active": False})
            request.route_id = False
            request.attempt_seq += 1

    def _seed_steps(self):
        self.ensure_one()
        steps = self.env["disbursement.step"].create(
            [
                {
                    "request_id": self.id,
                    "station_id": line.station_id.id,
                    "sequence": line.sequence,
                    "condition_domain": line.condition_domain,
                    "attempt_seq": self.attempt_seq,
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

    def _action_return_to_verification(self, reason):
        # Only whoever holds the request at its current station may send it back.
        for request in self.filtered("current_step_id"):
            request.current_step_id._check_act_allowed("return")
        return super()._action_return_to_verification(reason)

    # --------------------------------------------------------------- actions
    def action_station_complete(self):
        """Proceed: complete the current station's step."""
        for request in self:
            request.current_step_id.act("complete")
        return True

    def action_act_batch(self):
        """Proceed many requests at once from a work queue.

        Each request is processed in its own savepoint so one that fails (e.g.
        insufficient budget) does not roll back the rest; returns a summary
        notification.
        """
        done = self.browse()
        failures = []
        for record in self:
            try:
                with self.env.cr.savepoint():
                    record.action_station_complete()
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

    # ---------------------------------------------------------------- hooks
    def _station_check(self, code):
        """Raise UserError if the station ``code`` cannot be completed yet."""

    def _station_enter(self, code):
        """Side effect on entering the station ``code``."""

    def _station_complete(self, code):
        """Side effect on completing the station ``code``."""

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import plaintext2html

from .change_request_mixin import OUTSTANDING

ANSWER_ACTIVITY = "agx_change_request.mail_activity_change_request_answer"
# Bus notification telling the forms showing a record that its requests
# changed; it carries no content, they read them again with their own rights.
CHANGED_NOTIFICATION = "agx_change_request/changed"


def bus_channel(res_model, res_id):
    """The bus channel of the Change requests of one record."""
    return "agx_change_request:%s:%s" % (res_model, res_id)


class ChangeRequest(models.Model):
    """A request on a record asking its maker to fix or explain something
    (see CONTEXT.md).

    Users never touch this model directly (only system users have an ACL):
    the ``request_*`` methods below check the record itself — whoever can read
    it may make, answer and follow its requests — and let only the author
    change or delete theirs. Every step is posted on the record's chatter.
    """

    _name = "change.request"
    _description = "Change Request"
    _order = "id"

    res_model = fields.Char(string="Document Model", required=True, index=True)
    res_id = fields.Many2oneReference(
        string="Document", model_field="res_model", required=True, index=True
    )
    text = fields.Text(required=True)
    author_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="restrict",
        default=lambda self: self.env.user,
    )
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("answered", "Answered"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="open",
        index=True,
    )
    assignee_ids = fields.Many2many(
        comodel_name="res.users",
        relation="change_request_assignee_rel",
        column1="request_id",
        column2="user_id",
        string="Assignees",
    )
    reply_ids = fields.One2many(
        comodel_name="change.request.reply", inverse_name="request_id"
    )
    closed_uid = fields.Many2one(comodel_name="res.users", string="Closed by")
    closed_date = fields.Datetime(string="Closed on")
    cancel_reason = fields.Text()
    previous_texts = fields.Json(
        help="Earlier texts of an Edited request, oldest first: [{text, date}, ...].",
    )
    activity_ids = fields.One2many(
        comodel_name="mail.activity", inverse_name="change_request_id"
    )

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    @api.model
    def _get_readable_record(self, res_model, res_id):
        """The record (as the user) that takes Change requests, once the user
        is checked to read it."""
        Model = self.env.get(res_model)
        if Model is None or "change_request_count" not in Model._fields:
            raise UserError(_("This kind of document takes no change requests."))
        record = Model.browse(res_id).exists()
        if not record:
            raise UserError(_("This document no longer exists."))
        record.check_access_rights("read")
        record.check_access_rule("read")
        return record

    @api.model
    def _get_request(self, request_id):
        """The request (sudo), once the user is checked to read its record."""
        request = self.sudo().browse(request_id).exists()
        if not request:
            raise UserError(_("This change request no longer exists."))
        self._get_readable_record(request.res_model, request.res_id)
        return request

    def _get_record(self):
        """The record of this request, as the user (never sudo)."""
        self.ensure_one()
        return self.env(su=False)[self.res_model].browse(self.res_id)

    def _check_author(self):
        for request in self:
            if request.author_id != self.env.user:
                raise AccessError(_("Only its author can change a change request."))

    def _can_close(self):
        """Its author, or someone closing on the author's behalf."""
        self.ensure_one()
        # Not env.is_admin(): it holds for anyone in sudo.
        return (
            self.author_id == self.env.user
            or self.env.user._is_admin()
            or self._get_record()._change_request_can_close_on_behalf()
        )

    @api.model
    def _check_assignees(self, record, users):
        for user in users:
            readable = record.with_user(user).check_access_rights(
                "read", raise_exception=False
            ) and record.with_user(user)._filter_access_rules("read")
            if user.share or not readable:
                raise UserError(
                    _("%s cannot read this document and cannot be assigned.")
                    % user.name
                )

    # ------------------------------------------------------------------
    # Format
    # ------------------------------------------------------------------

    def _format(self):
        user = self.env.user
        result = []
        for request in self:
            is_own = request.author_id == user
            result.append(
                {
                    "id": request.id,
                    "res_model": request.res_model,
                    "res_id": request.res_id,
                    "text": request.text,
                    "state": request.state,
                    "author_id": request.author_id.id,
                    "author_name": request.author_id.name,
                    "create_date": fields.Datetime.to_string(request.create_date),
                    "assignees": [
                        {"id": u.id, "name": u.name} for u in request.assignee_ids
                    ],
                    "replies": request.reply_ids._format(),
                    "closed_name": request.closed_uid.name or "",
                    "closed_date": fields.Datetime.to_string(request.closed_date)
                    if request.closed_date
                    else False,
                    "cancel_reason": request.cancel_reason or "",
                    "previous_texts": request.previous_texts or [],
                    "is_own": is_own,
                    "can_reply": request.state in OUTSTANDING,
                    "can_close": request.state in ("open", "answered", "closed")
                    and request._can_close(),
                    "pin": False,
                }
            )
        return result

    # ------------------------------------------------------------------
    # Chatter and activities
    # ------------------------------------------------------------------

    def _post_step(self, summary, details=None, partners=None):
        """Post one step of this request on its record's chatter, as the
        user, even when they may not write on that chatter themselves."""
        self.ensure_one()
        body = Markup("<p>%s</p>") % summary
        if details:
            body += Markup("<p>%s</p>") % details
        self._get_record().sudo().message_post(
            body=body,
            subtype_xmlid="mail.mt_note",
            author_id=self.env.user.partner_id.id,
            partner_ids=partners.ids if partners else None,
        )
        # Every step is posted: forms showing the record catch up live.
        self.env["bus.bus"]._sendone(
            bus_channel(self.res_model, self.res_id),
            CHANGED_NOTIFICATION,
            {"res_model": self.res_model, "res_id": self.res_id},
        )

    def _label(self):
        self.ensure_one()
        return _("Change request #%(id)s: %(text)s", id=self.id, text=self.text)

    def _schedule(self, xmlid, users, summary):
        record = self._get_record().sudo()
        for user in users:
            activity = record.activity_schedule(
                xmlid,
                user_id=user.id,
                summary=summary,
                note=plaintext2html(self.text),
            )
            activity.change_request_id = self.id

    def _clear_activities(self, xmlid=None, users=None):
        activities = self.sudo().activity_ids
        if xmlid:
            activity_type = self.env.ref(xmlid)
            activities = activities.filtered(
                lambda a: a.activity_type_id == activity_type
            )
        if users is not None:
            activities = activities.filtered(lambda a: a.user_id in users)
        activities.unlink()

    def _schedule_answer(self, users):
        self._schedule(ANSWER_ACTIVITY, users, _("Answer a change request"))

    # ------------------------------------------------------------------
    # Steps (called as the user; they work in sudo once checked)
    # ------------------------------------------------------------------

    @api.model
    def _create_request(self, record, text, assignees=None, values=None):
        """Make a request on ``record`` (checked readable by the caller)."""
        text = (text or "").strip()
        if not text:
            raise UserError(_("Write the change request first."))
        assignees = (assignees or self.env["res.users"]) - self.env.user
        self._check_assignees(record, assignees)
        request = self.sudo().create(
            dict(
                values or {},
                res_model=record._name,
                res_id=record.id,
                text=text,
                author_id=self.env.uid,
                assignee_ids=[(6, 0, assignees.ids)],
            )
        )
        record.sudo().message_subscribe(partner_ids=assignees.partner_id.ids)
        request._schedule_answer(assignees)
        request._post_step(
            _("Change request made"),
            request._label(),
            partners=assignees.partner_id,
        )
        return request

    def _update_request(self, text=None, assignees=None):
        """Change the text or the Assignees: the author only, at any time."""
        self.ensure_one()
        self._check_author()
        if text is not None:
            text = text.strip()
            if not text:
                raise UserError(_("A change request cannot be empty."))
            if text != self.text:
                old = self.text
                self.write(
                    {
                        "text": text,
                        "previous_texts": (self.previous_texts or [])
                        + [
                            {
                                "text": old,
                                "date": fields.Datetime.to_string(
                                    fields.Datetime.now()
                                ),
                            }
                        ],
                    }
                )
                self._post_step(
                    _("Change request #%s edited", self.id),
                    _("%(old)s → %(new)s", old=old, new=text),
                )
        if assignees is not None:
            assignees -= self.author_id
            added = assignees - self.assignee_ids
            removed = self.assignee_ids - assignees
            if added or removed:
                self._check_assignees(self._get_record(), added)
                self._get_record().sudo().message_subscribe(
                    partner_ids=added.partner_id.ids
                )
                self.assignee_ids = [(6, 0, assignees.ids)]
                self._clear_activities(ANSWER_ACTIVITY, removed)
                if self.state == "open":
                    self._schedule_answer(added)
                self._post_step(
                    _("Change request #%s assigned", self.id),
                    ", ".join(assignees.mapped("name")) or _("Nobody"),
                    partners=added.partner_id,
                )

    def _delete_request(self):
        """Delete it: the author only, at any time; its text stays in the
        chatter."""
        self._check_author()
        for request in self:
            request._post_step(_("Change request deleted"), request._label())
        self._clear_activities()
        self.unlink()

    def _reply(self, body):
        """Add a Reply: anyone who reads the record, its author included.

        A reply from someone else answers the request; its author replying to
        an answered one (e.g. "still missing") opens it again, giving the
        Assignees their activity back. Nobody is notified otherwise.
        """
        self.ensure_one()
        if self.state not in OUTSTANDING:
            raise UserError(_("This change request is no longer open."))
        body = (body or "").strip()
        if not body:
            raise UserError(_("Write a reply first."))
        self.env["change.request.reply"].sudo().create(
            {"request_id": self.id, "author_id": self.env.uid, "body": body}
        )
        if self.author_id != self.env.user:
            if self.state == "open":
                self.state = "answered"
            self._clear_activities(ANSWER_ACTIVITY)
        elif self.state == "answered":
            self.state = "open"
            self._schedule_answer(self.assignee_ids)
        self._post_step(
            _("Reply to change request #%s", self.id),
            _("%(text)s — %(reply)s", text=self.text, reply=body),
        )

    def _set_closed(self, closed):
        """Close or reopen it: its author, or someone on their behalf."""
        self.ensure_one()
        if not self._can_close():
            raise AccessError(_("Only its author can close a change request."))
        if closed and self.state not in OUTSTANDING:
            raise UserError(_("Only an open or answered change request can be closed."))
        if not closed and self.state != "closed":
            raise UserError(_("Only a closed change request can be reopened."))
        on_behalf = self.author_id != self.env.user
        if closed:
            self.write(
                {
                    "state": "closed",
                    "closed_uid": self.env.uid,
                    "closed_date": fields.Datetime.now(),
                }
            )
            self._clear_activities()
            summary = (
                _("Change request #%(id)s closed on behalf of %(author)s")
                if on_behalf
                else _("Change request #%(id)s closed")
            )
        else:
            self.write({"state": "open", "closed_uid": False, "closed_date": False})
            self._clear_activities()
            self._schedule_answer(self.assignee_ids)
            summary = (
                _("Change request #%(id)s reopened on behalf of %(author)s")
                if on_behalf
                else _("Change request #%(id)s reopened")
            )
        self._post_step(
            summary % {"id": self.id, "author": self.author_id.name},
            self.text,
            partners=None if closed else self.assignee_ids.partner_id,
        )

    def _cancel(self, reason):
        """End requests that cannot be followed any more, e.g. once the file
        their pin is on is deleted; closed ones stay closed."""
        for request in self.filtered(lambda r: r.state in OUTSTANDING):
            request.write({"state": "cancelled", "cancel_reason": reason})
            request._clear_activities()
            request._post_step(
                _("Change request #%s cancelled", request.id),
                _("%(text)s — %(reason)s", text=request.text, reason=reason),
            )

    # ------------------------------------------------------------------
    # RPC used by the side panel
    # ------------------------------------------------------------------

    @api.model
    def request_load(self, res_model, res_id):
        record = self._get_readable_record(res_model, res_id)
        requests = self.sudo().search(
            [("res_model", "=", record._name), ("res_id", "=", record.id)]
        )
        return {
            "requests": requests._format(),
            "suggestions": self._assignee_suggestions(record),
        }

    @api.model
    def _assignee_suggestions(self, record):
        """Followers who are internal users able to read the record, but the
        user: suggested, never assigned by default."""
        users = record.sudo().message_partner_ids.user_ids.filtered(
            lambda u: not u.share and u.active and u != self.env.user
        )
        result = []
        for user in users:
            readable = record.with_user(user).check_access_rights(
                "read", raise_exception=False
            ) and record.with_user(user)._filter_access_rules("read")
            if readable:
                result.append({"id": user.id, "name": user.name})
        return result

    @api.model
    def request_count(self, res_model, res_id):
        record = self._get_readable_record(res_model, res_id)
        return len(record._get_outstanding_change_requests())

    @api.model
    def request_create(self, res_model, res_id, text, assignee_ids=()):
        record = self._get_readable_record(res_model, res_id)
        assignees = self.env["res.users"].browse(list(assignee_ids)).exists()
        return self._create_request(record, text, assignees)._format()[0]

    @api.model
    def request_update(self, request_id, vals):
        request = self._get_request(request_id)
        assignees = None
        if "assignee_ids" in vals:
            assignees = (
                self.env["res.users"].browse(list(vals["assignee_ids"])).exists()
            )
        request._update_request(text=vals.get("text"), assignees=assignees)
        return request._format()[0]

    @api.model
    def request_delete(self, request_id):
        self._get_request(request_id)._delete_request()
        return True

    @api.model
    def request_reply(self, request_id, body):
        request = self._get_request(request_id)
        request._reply(body)
        return request._format()[0]

    @api.model
    def request_set_closed(self, request_id, closed):
        request = self._get_request(request_id)
        request._set_closed(bool(closed))
        return request._format()[0]

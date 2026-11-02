from odoo import fields, models

OUTSTANDING = ("open", "answered")


class ChangeRequestMixin(models.AbstractModel):
    """Lets a model take Change requests (ADR-0001), like
    ``mail.activity.mixin`` lets it take activities: the form gets the
    Change requests button and side panel, and its files may carry pinned
    requests (``agx_photoviewer_change_request``).

    The model must already inherit ``mail.thread`` and ``mail.activity.mixin``
    (steps go to its chatter, Assignees get activities). The mixin does not
    inherit them itself: listed after them on an existing model, it would
    make the method resolution order inconsistent.
    """

    _name = "change.request.mixin"
    _description = "Change Request Mixin"

    change_request_count = fields.Integer(
        string="Outstanding Change Requests",
        compute="_compute_change_request_count",
    )

    def _compute_change_request_count(self):
        requests = self._get_outstanding_change_requests()
        for record in self:
            record.change_request_count = len(
                requests.filtered(lambda request, r=record: request.res_id == r.id)
            )

    def _get_outstanding_change_requests(self):
        """Change requests of these records still open or answered, whoever
        made them (sudo). A module refusing a step while some are
        outstanding counts them all."""
        ids = [record_id for record_id in self.ids if isinstance(record_id, int)]
        if not ids:
            return self.env["change.request"].sudo()
        return (
            self.env["change.request"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", ids),
                    ("state", "in", OUTSTANDING),
                ]
            )
        )

    def _change_request_can_close_on_behalf(self):
        """Whether the current user may close or reopen the Change requests
        of this record on their author's behalf, besides administrators.
        Never by default; the module of the record says who, e.g. a Buddy."""
        self.ensure_one()
        return False

    def unlink(self):
        requests = (
            self.env["change.request"]
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "in", self.ids)])
        )
        res = super().unlink()
        requests.unlink()
        return res

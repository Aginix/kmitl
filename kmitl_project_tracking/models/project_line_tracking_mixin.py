from odoo import models


class ProjectLineTrackingMixin(models.AbstractModel):
    """A project line sharing its project with a sibling One2many (same comodel,
    split by a type field) is logged only under the One2many of its own type;
    tracking_manager would otherwise log it under every flagged sibling."""

    _name = "project.line.tracking.mixin"
    _description = "Project Line Tracking Mixin"

    _line_type_field = "line_type"
    _line_o2m = {}

    def _tm_get_fields_to_notify(self):
        notify = super()._tm_get_fields_to_notify()
        own = self._line_o2m.get(self[self._line_type_field])
        return [n for n in notify if n[1] == own] if own else notify

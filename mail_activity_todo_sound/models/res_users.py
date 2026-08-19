from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    todo_sound_enabled = fields.Boolean(
        string="Play a sound on a new Todo",
        default=True,
        help="Play a short sound when a new Todo lands in your inbox. Off silences "
        "the whole inbox; per-source control (e.g. e-Saraban) is added by its bridge.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        # A user must read their own preference to render the toggle.
        return super().SELF_READABLE_FIELDS + ["todo_sound_enabled"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        # A user sets their own notification-sound preference (Preferences).
        return super().SELF_WRITEABLE_FIELDS + ["todo_sound_enabled"]

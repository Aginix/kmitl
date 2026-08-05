from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    todo_sound_sarabun_enabled = fields.Boolean(
        string="Play a sound on a new e-Saraban Todo",
        default=True,
        help="Independent of the general Todo sound (ADR-0014): keep e-Saraban "
        "หนังสือ audible even when you have silenced general Todos. Effective only "
        "with the Todo notification-sound add-on installed.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["todo_sound_sarabun_enabled"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["todo_sound_sarabun_enabled"]

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    signature_image = fields.Image(
        string="Digital Signature",
        max_width=1024,
        max_height=1024,
        attachment=True,
        help="Personal digital signature, captured into approval documents at approval time.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["signature_image"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["signature_image"]

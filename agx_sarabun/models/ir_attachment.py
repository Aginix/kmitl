"""Lock the ความเห็นในการลงนาม files (เอกสารประกอบการลงนาม)."""
from odoo import _, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def check(self, mode, values=None):
        # A signer's evidence: anyone who reads the หนังสือ may download it, but only
        # the engine (sudo) may change or delete it — not a writer of the หนังสือ.
        if mode in ("write", "unlink") and self and not self.env.su:
            self.env.cr.execute(
                "SELECT 1 FROM sarabun_routing_step_sign_attachment_rel "
                "WHERE attachment_id IN %s LIMIT 1",
                [tuple(self.ids)],
            )
            if self.env.cr.fetchone():
                raise AccessError(
                    _("A file attached to a signature (เอกสารประกอบการลงนาม) cannot be "
                      "changed or deleted.")
                )
        return super().check(mode, values=values)

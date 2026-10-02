from odoo import models


class IrAttachment(models.Model):
    # Core defaults to 'id desc' (newest first), which shows attachments in
    # reverse of the order they were uploaded. Users read attachment lists
    # as a timeline (oldest → newest), so flip the default. Any caller that
    # needs newest-first can still pass order= explicitly on search().
    _inherit = "ir.attachment"
    _order = "id asc"

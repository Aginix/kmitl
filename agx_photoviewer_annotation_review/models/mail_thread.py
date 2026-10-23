from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_mail_thread_data_attachments(self):
        # A record shows only the latest revision of each file.
        return (
            super()
            ._get_mail_thread_data_attachments()
            .filtered(lambda attachment: not attachment.revision_superseded)
        )

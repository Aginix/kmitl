from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        res = super().session_info()
        res["attachment_logging_kmitl_enabled"] = bool(
            self.env["ir.attachment"]._is_use_attachment_log()
        )
        return res

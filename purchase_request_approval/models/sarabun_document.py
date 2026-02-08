# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def action_send(self):
        """Override to trigger callback when document is sent."""
        res = super().action_send()

        # Trigger callback on origin record
        for record in self:
            if record.origin_model and record.origin_res_id:
                try:
                    origin_record = self.env[record.origin_model].sudo().browse(
                        record.origin_res_id
                    )
                    if origin_record.exists() and hasattr(origin_record, "_on_sarabun_sent"):
                        _logger.info(
                            "Calling _on_sarabun_sent on %s (id=%s)",
                            record.origin_model,
                            record.origin_res_id,
                        )
                        origin_record._on_sarabun_sent(record)
                except Exception as e:
                    _logger.exception(
                        "Error calling _on_sarabun_sent on %s (id=%s): %s",
                        record.origin_model,
                        record.origin_res_id,
                        str(e),
                    )

        return res

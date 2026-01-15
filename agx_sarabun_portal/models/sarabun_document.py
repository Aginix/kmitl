# -*- coding: utf-8 -*-
from odoo import models


class SarabunDocument(models.Model):
    _name = "sarabun.document"
    _inherit = ["sarabun.document", "portal.mixin"]

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for document in self:
            document.access_url = f"/my/sarabun_document/{document.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Sarabun Document-%s' % (self.name)

    def open_preview(self):
        if self.id:
            return {
                'type': 'ir.actions.act_url',
                'url': self.access_url,
                'target': 'new',
            }


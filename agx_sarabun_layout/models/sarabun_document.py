# -*- coding: utf-8 -*-
from odoo import models


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def _get_no_source_report_ref(self):
        report = self.type_id.report_template_id
        return report.report_name if report else super()._get_no_source_report_ref()

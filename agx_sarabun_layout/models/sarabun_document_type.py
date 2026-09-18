# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunDocumentType(models.Model):
    _inherit = "sarabun.document.type"

    report_template_id = fields.Many2one(
        "ir.actions.report",
        string="Document Layout",
        domain="[('model', '=', 'sarabun.document')]",
        help="QWeb layout used to render this type's official document "
        "(no-source path). Leave empty to use the default บันทึกข้อความ layout.",
    )

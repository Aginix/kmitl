# -*- coding: utf-8 -*-
from odoo import fields, models


class HrPreboardingDocument(models.Model):
    _name = "hr.preboarding.document"
    _description = "Preboarding Document Checklist"

    preboarding_id = fields.Many2one(
        "hr.preboarding", required=True, ondelete="cascade"
    )
    name = fields.Char("Document Name", required=True)
    required = fields.Boolean("Required", default=False)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    state = fields.Selection(
        [("pending", "Pending"), ("uploaded", "Uploaded")], default="pending"
    )

# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunDocumentType(models.Model):
    _name = "sarabun.document.type"
    _description = "Sarabun Document Type"
    _order = "sequence, name"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    code = fields.Selection(
        selection=[
            ("memo", "Internal Memo"),
            ("circular", "Circular"),
            ("from_record", "From Record"),
        ],
        string="Type Code",
        required=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Document Sequence",
    )
    default_route_template_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Default Route Template",
    )

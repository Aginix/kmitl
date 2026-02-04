# Copyright 2021 Ecosoft (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    kmitl_project_ids = fields.Many2many(
        comodel_name="kmitl.project",
        string="Projects",
    )
    model = fields.Selection(
        selection_add=[
            ("kmitl.project", "KMITL Project"),
        ],
        ondelete={"kmitl.project": "cascade"},
    )

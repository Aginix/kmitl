from odoo import models


class ProjectOutput(models.Model):
    _name = "project.output"
    _inherit = ["project.output", "project.line.tracking.mixin"]

    _line_o2m = {"output": "output_ids", "outcome": "outcome_ids"}

from odoo import models


class ProjectTarget(models.Model):
    _name = "project.target"
    _inherit = ["project.target", "project.line.tracking.mixin"]

    _line_o2m = {
        "target": "target_ids",
        "participant": "participant_ids",
        "organizer": "organizer_ids",
    }

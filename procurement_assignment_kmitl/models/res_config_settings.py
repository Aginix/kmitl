# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    allow_takeover_assigned = fields.Boolean(
        string="Allow officers to take over already-assigned documents",
        config_parameter="procurement_assignment_kmitl.allow_takeover_assigned",
        help="When enabled, any procurement officer can use 'Assign to me' to "
        "take over a document already assigned to someone else. When disabled "
        "(default), officers may only claim unassigned documents; reassigning "
        "is a manager action.",
    )

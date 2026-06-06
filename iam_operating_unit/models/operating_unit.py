# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models


class OperatingUnit(models.Model):
    _inherit = "operating.unit"

    iam_user_count = fields.Integer(
        string="# Users",
        compute="_compute_iam_user_count",
        help="Number of users assigned to this operating unit.",
    )

    @api.depends("user_ids")
    def _compute_iam_user_count(self):
        # sudo for a robust count regardless of the reader's res.users rules;
        # only an integer is surfaced. user_ids ("Users Allowed") are the users
        # explicitly assigned to the OU (not the all-OU managers).
        for ou in self:
            ou.iam_user_count = len(ou.sudo().user_ids)

# Copyright 2025 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    budget_allow_negative = fields.Boolean(
        string="อนุญาตงบประมาณติดลบ",
        config_parameter="budget.allow_negative",
        default=False,
        help="อนุญาตให้มีรายการที่ทำให้งบประมาณติดลบ",
    )
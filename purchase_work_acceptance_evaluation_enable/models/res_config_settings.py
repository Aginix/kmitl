# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.onchange("group_enable_eval_on_wa")
    def _onchange_group_enable_eval_on_wa(self):
        self.group_enable_eval_on_wa = True

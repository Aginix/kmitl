# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CommentWizard(models.TransientModel):
    _inherit = 'comment.wizard'

    comment = fields.Char(required=False)
    comment_selection = fields.Selection(
        selection=[
            ('leave', 'Leave'),
            ('mission', 'Mission'),
        ],
        string='Comment',
    )

    is_wa_model = fields.Boolean(
        compute='_compute_is_wa_model',
    )

    @api.depends('res_model')
    def _compute_is_wa_model(self):
        for rec in self:
            rec.is_wa_model = rec.res_model == 'work.acceptance'

    def add_comment(self):
        if self.is_wa_model:
            self.comment = self.comment_selection or ''
        return super().add_comment()

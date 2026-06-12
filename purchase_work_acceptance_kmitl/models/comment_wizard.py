# -*- coding: utf-8 -*-

from odoo import fields, models


class CommentWizard(models.TransientModel):
    _inherit = "comment.wizard"

    comment = fields.Char(required=False)
    wa_reason = fields.Selection(
        selection=[
            ("leave", "ลา"),
            ("on_duty", "ติดภารกิจ"),
        ],
        string="Reason",
    )

    def add_comment(self):
        if self.res_model == "work.acceptance" and self.wa_reason:
            self.comment = self.wa_reason
        return super().add_comment()

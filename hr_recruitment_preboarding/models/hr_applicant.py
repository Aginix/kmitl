# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    preboarding_ids = fields.One2many(
        "hr.preboarding", "applicant_id", "Pre-boarding Records"
    )
    preboarding_count = fields.Integer(compute="_compute_preboarding_count")

    @api.depends("preboarding_ids")
    def _compute_preboarding_count(self):
        for rec in self:
            rec.preboarding_count = len(rec.preboarding_ids)

    def action_open_preboarding(self):
        self.ensure_one()
        preboarding = self.preboarding_ids[:1]
        if not preboarding:
            preboarding = self.env["hr.preboarding"].create(
                {"applicant_id": self.id}
            )
            preboarding._create_default_documents()
        return {
            "type": "ir.actions.act_window",
            "name": "รายงานตัว",
            "res_model": "hr.preboarding",
            "res_id": preboarding.id,
            "view_mode": "form",
            "target": "current",
        }

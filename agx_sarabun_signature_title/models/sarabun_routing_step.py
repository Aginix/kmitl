# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    signed_academic_title = fields.Char(
        string="คำนำหน้า/ตำแหน่งที่ลงนาม (snapshot)",
        readonly=True,
        copy=False,
    )

    def _signature_snapshot_vals(self, actor, capacity=False):
        vals = super()._signature_snapshot_vals(actor, capacity=capacity)
        vals["signed_academic_title"] = (
            actor.sudo().employee_id.academic_standing_title or ""
        )
        return vals

    def _signed_display_name(self):
        self.ensure_one()
        name = (
            self.signed_name
            or self.acted_by_id.employee_id.name
            or self.acted_by_id.name
            or ""
        )
        title = (
            self.signed_academic_title
            or self.acted_by_id.employee_id.academic_standing_title
            or ""
        )
        return ("%s %s" % (title, name)).strip()

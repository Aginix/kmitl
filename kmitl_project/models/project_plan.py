# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectPlan(models.Model):
    _name = _description = "project.plan"
    _order = "sequence"

    name = fields.Char(string="ชื่อ", required=True)
    sequence = fields.Integer(string="ลำดับการแสดงผล")
    amount = fields.Float(string="งบประมาณ")
    percentage = fields.Integer(string="ร้อยละ")
    m1 = fields.Boolean(string="ม.ค.")
    m2 = fields.Boolean(string="ก.พ.")
    m3 = fields.Boolean(string="มี.ค.")
    m4 = fields.Boolean(string="เม.ย.")
    m5 = fields.Boolean(string="พ.ค.")
    m6 = fields.Boolean(string="มิ.ย.")
    m7 = fields.Boolean(string="ก.ค.")
    m8 = fields.Boolean(string="ส.ค.")
    m9 = fields.Boolean(string="ก.ย.")
    m10 = fields.Boolean(string="ต.ค.")
    m11 = fields.Boolean(string="พ.ย.")
    m12 = fields.Boolean(string="ธ.ค.")
    project_id = fields.Many2one("kmitl.project", string="โครงการ")

    @api.constrains("percentage")
    def _check_percentage(self):
        for rec in self:
            if rec.percentage < 0 or rec.percentage > 100:
                raise ValidationError(_("Percentage must be 0-100"))

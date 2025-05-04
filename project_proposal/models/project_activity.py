# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectActivity(models.Model):
    _name = "project.activity"
    _description = "ProjectActivity"

    name = fields.Char(string="ชื่อ")
    seq = fields.Integer(string="ลำดับการแสดงผล")
    amount = fields.Float(string="งบประมาณ")
    line_type = fields.Selection(
        [("activity", "กิจกรรม"), ("plan", "ขั้นตอน")], string="ประเภท"
    )
    # ขาด parent_id กำลังทำความเข้าใจ
    m1 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 1 ประจำปีงบประมาณ")
    m2 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 2 ประจำปีงบประมาณ")
    m3 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 3 ประจำปีงบประมาณ")
    m4 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 4 ประจำปีงบประมาณ")
    m5 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 5 ประจำปีงบประมาณ")
    m6 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 6 ประจำปีงบประมาณ")
    m7 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 7 ประจำปีงบประมาณ")
    m8 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 8 ประจำปีงบประมาณ")
    m9 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 9 ประจำปีงบประมาณ")
    m10 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 10 ประจำปีงบประมาณ")
    m11 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 11 ประจำปีงบประมาณ")
    m12 = fields.Boolean(string="แผนการดำเนินงานเดือนที่ 12 ประจำปีงบประมาณ")
    project_kmitl_id = fields.Many2one("project.kmitl", string="โครงการ")

    @api.onchange("line_type")
    def _onchange_line_type(self):
        if self.line_type != "activity":
            self.amount = None

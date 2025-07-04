# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ProjectActivity(models.Model):
    _name = 'project.activity'
    _description = 'ProjectActivity'

    name = fields.Char(string="ชื่อ")
    seq = fields.Integer(string="ลำดับการแสดงผล")
    amount = fields.Float(string="งบประมาณ")
    line_type = fields.Selection(
        [("activity", "กิจกรรม"), ("plan", "ขั้นตอน")], string="ประเภท"
    )
    percentage = fields.Float(string="ร้อยละ", digits=(5, 2))
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
    project_kmitl_id = fields.Many2one("project.project", string="โครงการ", readonly=True)

    @api.onchange("line_type")
    def _onchange_line_type(self):
        if self.line_type != "activity":
            self.amount = None
            self.amount = None
            self.amount = None
            self.amount = None
            self.amount = None

# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectActivity(models.Model):
    _name = "project.activity"
    _description = "ProjectActivity"
    _description = "Project Activity"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "parent_path, seq"

    name = fields.Char(string="ชื่อ")
    seq = fields.Integer(string="ลำดับการแสดงผล")
    amount = fields.Float(string="งบประมาณ")
    line_type = fields.Selection(
        [("activity", "กิจกรรม"), ("plan", "ขั้นตอน")], string="ประเภท"
    )
    parent_id = fields.Many2one(
        "project.activity", string="รายการแม่", index=True, ondelete="cascade"
    )
    child_ids = fields.One2many("project.activity", "parent_id", string="รายการย่อย")
    parent_path = fields.Char(index=True)
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
    project_kmitl_id = fields.Many2one("project.kmitl", string="โครงการ", readonly=True)

    @api.onchange("line_type")
    def _onchange_line_type(self):
        if self.line_type != "activity":
            self.amount = None

    @api.model
    def create(self, vals):
        skip_names = [
            "วางแผนการดําเนินงาน",
            "ดําเนินงานตามแผน",
            "สรุป/ประเมินผลการดําเนินงาน",
            "รายงานผลโครงการ",
        ]

        if vals.get("name") in skip_names:
            return super(ProjectActivity, self).create(vals)

        if vals.get("project_kmitl_id") and not vals.get("parent_id"):
            parent_activity = self.env["project.activity"].search(
                [
                    ("project_kmitl_id", "=", vals["project_kmitl_id"]),
                    ("name", "=", "ดําเนินงานตามแผน"),
                ],
                limit=1,
            )
            if parent_activity:
                vals["parent_id"] = parent_activity.id
        return super(ProjectActivity, self).create(vals)

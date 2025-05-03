# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectKmitl(models.Model):
    _name = "project.kmitl"
    _description = "ProjectKmitl"

    name = fields.Char(string="ชื่อโครงการ")
    source = fields.Selection(
        [("national_budget", "เงินงบประมาณแผ่นดิน"), ("income_budget", "เงินรายได้")],
        string="ประเภทแหล่งเงิน",
    )
    introduction = fields.Html(string="หลักการและเหตุผล", sanitize_attributes=False)
    national_strategy_id = fields.Integer(string="ความสอดคล้องกับยุทธศาสตร์")
    impact_ids = fields.Many2many("project.impact", string="Impact")
    global_index_ids = fields.Many2many("project.global.index", string="Global Index")
    okr_1 = fields.Many2many(
        "project.okr", string="Objective Key Result (OKR)(ตัวชี้วัดตามแผนบริหารสถาบัน)"
    )
    fight_ids = fields.Many2many("project.fight", string="ความสอดคล้องกับค่านิยม")
    objective_ids = fields.One2many(
        comodel_name="project.objectives",
        inverse_name="project_kmitl_id",
        string="วัตถุประสงค์ของโครงการ",
    )
    # department_id = fields.Integer(string="หน่วยงานผู้รับผิดชอบโครงการ")
    # department_name = fields.Char(string="หน่วยงานผู้รับผิดชอบโครงการ")
    location = fields.Text(string="ระยะเวลาดําเนินโครงการ")
    methodology = fields.Selection(
        [
            ("describe", "บรรยาย"),
            ("lecture", "บรรยายเชิงปฏิบัติการ"),
            ("exhibition", "นิทรรศการ"),
            ("other", "อื่น ๆ"),
        ],
        string="วิธีดำเนินการ",
    )
    methodology_description = fields.Text(string="วิธีดำเนินการ ระบุ")
    output_ids = fields.One2many(
        comodel_name="project.output",
        inverse_name="project_kmitl_id",
        string="เป้าหมาย ผลผลิต และผลลัพธ์",
    )
    expected_result = fields.Text(string="ผลที่คาดว่าจะได้รับ")
    evaluation_method_ids = fields.Many2many(
        "project.evaluation.methods", string="วิธีการ/เครื่องมือติดตามและประเมินผล มีตัวเลือกดังนี้"
    )
    evaluation_method_description = fields.Text(
        string="วิธีการ/เครื่องมือติดตามและประเมินผล ระบุ"
    )
    user_id = fields.Many2one(
        "res.users", string="ผู้รับผิดชอบข้อมูล", default=lambda self: self.env.user
    )
    attachment_ids = fields.Binary(string="เอกสารประกอบการพิจารณาโครงการ")

    @api.onchange("methodology")
    def _onchange_methodology(self):
        mapping = {
            "describe": "บรรยาย",
            "lecture": "บรรยายเชิงปฏิบัติการ",
            "exhibition": "นิทรรศการ",
            "other": "อื่น ๆ",
        }
        if self.methodology:
            first_line = mapping.get(self.methodology, "")
            current_text = self.methodology_description or ""
            other_lines = (
                "\n".join(current_text.split("\n")[1:]) if current_text else ""
            )
            self.methodology_description = f"{first_line}\n{other_lines}".strip()

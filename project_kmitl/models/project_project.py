# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
    )
    name = fields.Char(string="ชื่อโครงการ")
    source = fields.Selection(
        [("national_budget", "เงินงบประมาณแผ่นดิน"), ("income_budget", "เงินรายได้")],
        string="ประเภทแหล่งเงิน",
    )
    introduction = fields.Html(string="หลักการและเหตุผล", sanitize_attributes=False)
    national_strategy_id = fields.Many2one('project.strategic.plan',string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 1",domain="[('level', '=', 1)]")
    master_plan_id = fields.Many2one('project.strategic.plan',string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 2",domain="[('level', '=', 2)]")
    nesdc_plan_id = fields.Many2one('project.strategic.plan',string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 2 ฉบับที่ 13",domain="[('level', '=', 2)]")
    kmitl_plan_id = fields.Many2one('project.strategic.plan',string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 3",domain="[('level', '=', 3)]")
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
    department_id = fields.Many2one(
        comodel_name="hr.department", compute="_compute_department_id", string="หน่วยงานผู้รับผิดชอบโครงการ", index=True, store=True,
    )
    department_name = fields.Char(
        string="ชื่อหน่วยงานผู้รับผิดชอบโครงการ", related="department_id.name", store=True
    )
    project_manager_name = fields.Char(
    string="หัวหน้าโครงการ",
    related='user_id.partner_id.name',
    store=True,
    readonly=True
    )

    project_manager_position = fields.Char(
        string="หัวหน้าโครงการ ตำแหน่ง",
        related='user_id.partner_id.function',
        store=True,
        readonly=True
    )

    project_manager_tel = fields.Char(
        string="หัวหน้าโครงการ เบอร์โทร",
        related='user_id.partner_id.phone',
        store=True,
        readonly=True
    )

    project_manager_email = fields.Char(
        string="หัวหน้าโครงการ อีเมล",
        related='user_id.partner_id.email',
        store=True,
        readonly=True
    )
    location = fields.Text(string="สถานที่/พื้นที่ดำเนินโครงการ")
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
    target_ids = fields.Text(string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ")
    output_ids = fields.One2many(
        comodel_name="project.output",
        inverse_name="project_kmitl_id",
        string="เป้าหมาย ผลผลิต และผลลัพธ์",
    )
    responsible_id = fields.Many2one('res.users', string="ผู้รับผิดชอบข้อมูล")
    project_activity_ids = fields.One2many(
        comodel_name="project.activity",
        inverse_name="project_kmitl_id",
        string="แผนการดําเนินงานและแผนการใช้จ่ายงบประมาณ",
    )
    expected_result = fields.Text(string="ผลที่คาดว่าจะได้รับ")
    evaluation_method_ids = fields.Many2many(
        "project.evaluation.methods", string="วิธีการ/เครื่องมือติดตามและประเมินผล มีตัวเลือกดังนี้"
    )
    evaluation_method_description = fields.Text(
        string="วิธีการ/เครื่องมือติดตามและประเมินผล ระบุ"
    )
    attachment_ids = fields.Binary(string="เอกสารประกอบการพิจารณาโครงการ")
    total_budget = fields.Float(string="จำนวนงบประมาณทั้งหมด")
    state = fields.Selection(
        [
            ("draft", "แบบร่าง"),
            ("submit", "แบบร่างเสนอเจ้าภาพ"),
            ("validate", "ตรวจสอบข้อมูล"),
            ("approve", "อนุมัติโครงการ"),
            ("cancel", "ยกเลิกโครงการ"),
        ],
        string="สถานะการขออนุมัติโครงการ",
        default="draft",
    )

    @api.depends('user_id')
    def _compute_department_id(self):
        for record in self:
            employee = self.env['hr.employee'].search([('user_id', '=', record.user_id.id)], limit=1)
            record.department_id = employee.department_id if employee else False

    def action_submit(self):
        for record in self:
            record.state = 'submit'

    def action_validate(self):
        for record in self:
            record.state = 'validate'

    def action_approve(self):
        for record in self:
            record.state = 'approve'

    def action_cancel(self):
        for record in self:
            record.state = 'cancel'

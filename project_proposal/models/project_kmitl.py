import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProjectKmitl(models.Model):
    _name = "project.kmitl"
    _description = "ProjectKmitl"
    _inherit = ["mail.thread"]

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
    department_id = fields.Many2one(
        comodel_name="hr.department", string="หน่วยงานผู้รับผิดชอบโครงการ"
    )
    department_name = fields.Char(
        string="=ชื่อหน่วยงานผู้รับผิดชอบโครงการ", related="department_id.name", store=True
    )
    project_manager_name = fields.Char(string="หัวหน้าโครงการ")
    project_manager_position = fields.Char(string="หัวหน้าโครงการ ตำแหน่ง")
    project_manager_tel = fields.Char(string="หัวหน้าโครงการ เบอร์โทร")
    project_manager_email = fields.Char(string="หัวหน้าโครงการ อีเมล")
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
    activity_ids = fields.One2many(
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
    user_id = fields.Many2one(
        "res.users", string="ผู้รับผิดชอบข้อมูล", default=lambda self: self.env.user
    )
    attachment_ids = fields.Binary(string="เอกสารประกอบการพิจารณาโครงการ")
    total_budget = fields.Float(string="จำนวนงบประมาณทั้งหมด")
    state = fields.Selection(
        [
            ("draft", "แบบร่าง"),
            ("submit", "กรอกข้อมูลเสร็จสิ้น"),
            ("pending", "อยู่ระหว่างพิจารณา"),
            ("approved", "อนุมัติโครงการแล้ว"),
        ],
        string="สถานะการขออนุมัติโครงการ",
        default="draft",
    )

    def action_next_state(self):
        for rec in self:
            if rec.state == "draft":
                rec.state = "submit"
            elif rec.state == "submit":
                rec.state = "pending"
            elif rec.state == "pending":
                rec.state = "approved"

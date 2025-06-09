import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "portal.mixin"]

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
    )
    name = fields.Char(string="ชื่อโครงการ", tracking=True)
    reference = fields.Char(string="เลขที่", default="แบบร่าง")
    source = fields.Selection(
        [("national_budget", "เงินงบประมาณแผ่นดิน"), ("income_budget", "เงินรายได้")],
        string="ประเภทแหล่งเงิน",
        tracking=True,
    )
    introduction = fields.Html(string="หลักการและเหตุผล", sanitize_attributes=False)
    national_strategy_id = fields.Many2one(
        "project.strategic.plan",
        string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 1",
        domain="[('level', '=', 1)]",
        tracking=True,
    )
    master_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 2",
        domain="[('level', '=', 2)]",
        tracking=True,
    )
    nesdc_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 2 ฉบับที่ 13",
        domain="[('level', '=', 2)]",
        tracking=True,
    )
    kmitl_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="ความสอดคล้องกับยุทธศาสตร์ แผนระดับที่ 3",
        domain="[('level', '=', 3)]",
        tracking=True,
    )
    impact_ids = fields.Many2many("project.impact", string="Impact", tracking=True)
    global_index_ids = fields.Many2many(
        "project.global.index", string="Global Index", tracking=True
    )
    okr_1 = fields.Many2many(
        "project.okr",
        string="Objective Key Result (OKR)(ตัวชี้วัดตามแผนบริหารสถาบัน)",
        tracking=True,
    )
    fight_ids = fields.Many2many(
        "project.fight", string="ความสอดคล้องกับค่านิยม", tracking=True
    )
    objective_ids = fields.One2many(
        comodel_name="project.objectives",
        inverse_name="project_kmitl_id",
        string="วัตถุประสงค์ของโครงการ",
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        string="หน่วยงานผู้รับผิดชอบโครงการ",
        index=True,
        store=True,
        tracking=True,
    )
    department_name = fields.Char(
        string="ชื่อหน่วยงานผู้รับผิดชอบโครงการ",
        related="department_id.name",
        store=True,
        tracking=True,
    )
    project_manager_name = fields.Char(
        string="หัวหน้าโครงการ",
        related="user_id.partner_id.name",
        store=True,
        readonly=True,
        tracking=True,
    )

    project_manager_position = fields.Char(
        string="หัวหน้าโครงการ ตำแหน่ง",
        related="user_id.partner_id.function",
        store=True,
        readonly=True,
        tracking=True,
    )

    project_manager_tel = fields.Char(
        string="หัวหน้าโครงการ เบอร์โทร",
        related="user_id.partner_id.phone",
        store=True,
        readonly=True,
        tracking=True,
    )

    project_manager_email = fields.Char(
        string="หัวหน้าโครงการ อีเมล",
        related="user_id.partner_id.email",
        store=True,
        readonly=True,
        tracking=True,
    )
    location = fields.Text(string="สถานที่/พื้นที่ดำเนินโครงการ", tracking=True)
    methodology = fields.Selection(
        [
            ("describe", "บรรยาย"),
            ("lecture", "บรรยายเชิงปฏิบัติการ"),
            ("exhibition", "นิทรรศการ"),
            ("other", "อื่น ๆ"),
        ],
        string="วิธีดำเนินการ",
        tracking=True,
    )
    methodology_description = fields.Text(string="วิธีดำเนินการ ระบุ", tracking=True)
    target_ids = fields.Text(string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ", tracking=True)
    output_ids = fields.One2many(
        comodel_name="project.output",
        inverse_name="project_kmitl_id",
        string="เป้าหมาย ผลผลิต และผลลัพธ์",
        tracking=True,
    )
    responsible_id = fields.Many2one("res.users", string="ผู้รับผิดชอบข้อมูล", tracking=True)
    project_activity_ids = fields.One2many(
        comodel_name="project.activity",
        inverse_name="project_kmitl_id",
        string="แผนการดําเนินงานและแผนการใช้จ่ายงบประมาณ",
        tracking=True,
    )
    expected_result = fields.Text(string="ผลที่คาดว่าจะได้รับ")
    evaluation_method_ids = fields.Many2many(
        "project.evaluation.methods",
        string="วิธีการ/เครื่องมือติดตามและประเมินผล มีตัวเลือกดังนี้",
        tracking=True,
    )
    evaluation_method_description = fields.Text(
        string="วิธีการ/เครื่องมือติดตามและประเมินผล ระบุ", tracking=True
    )
    attachment_ids = fields.Binary(string="เอกสารประกอบการพิจารณาโครงการ", tracking=True)
    total_budget = fields.Float(string="จำนวนงบประมาณทั้งหมด", tracking=True)
    state = fields.Selection(
        [
            ("draft", "แบบร่าง"),
            ("submit", "แบบร่างเสนอเจ้าภาพ"),
            ("validate", "ตรวจสอบข้อมูล"),
            ("approve", "อนุมัติโครงการ"),
            ("revised", "มีการปรับปรุงแก้ไข"),
            ("in_progress", "ระหว่างดำเนินการ"),
            ("done", "เสร็จสิ้น"),
            ("cancel", "ยกเลิกโครงการ"),
        ],
        string="สถานะการขออนุมัติโครงการ",
        default="draft",
    )
    change_type = fields.Selection(
        [("major", "กระทบแผน/งบประมาณ"), ("patch", "ไม่กระทบแผน/งบประมาณ")],
        string="แบบกระทบแผน/งบประมาณ​",
        default="major",
        tracking=True,
    )
    office_order_no = fields.Char(string="เลขที่หนังสืออนุมัติจากระบบ e-office", tracking=True)

    @api.depends("user_id")
    def _compute_department_id(self):
        for record in self:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", record.user_id.id)], limit=1
            )
            record.department_id = employee.department_id if employee else False

    def action_submit(self):
        for record in self:
            record.state = "submit"

    def action_validate(self):
        for record in self:
            record.state = "validate"

    def action_open_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.approve.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_project_id": self.id,
            },
        }

    def action_cancel(self):
        for record in self:
            record.state = "cancel"

    def _compute_access_url(self):
        for record in self:
            record.access_url = f"/projects/{record.id}"

    def action_open_public(self):
        self.ensure_one()
        self._portal_ensure_token()
        return {
            "type": "ir.actions.act_url",
            "url": self._get_share_url(),
            "target": "new",
        }

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

READONLY_STATES = {
    "confirmed": [("readonly", True)],
    "done": [("readonly", True)],
    "cancel": [("readonly", True)],
}

PROJECT_TYPE_SELECTION = [
    ("consulting", "ให้คำปรึกษา"),
    ("research_contract", "วิจัยตามสัญญา"),
    ("training", "ฝึกอบรม"),
    ("testing", "ทดสอบ/สอบเทียบ"),
    ("external_research", "วิจัยแหล่งทุนภายนอก"),
    ("internal_research", "วิจัยทุนภายใน"),
]

CLIENT_ORG_TYPE_SELECTION = [
    ("government", "หน่วยงานรัฐ"),
    ("state_enterprise", "รัฐวิสาหกิจ"),
    ("private", "เอกชน"),
    ("other", "อื่นๆ"),
]


class KrisProject(models.Model):
    _name = "kris.project"
    _description = "KRIS Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"
    _rec_name = "name"

    name = fields.Char(
        string="เลขที่เอกสาร",
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    project_name = fields.Char(
        string="ชื่อโครงการ",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    project_type = fields.Selection(
        selection=PROJECT_TYPE_SELECTION,
        string="ประเภทโครงการ",
        tracking=True,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("confirmed", "ยืนยัน"),
            ("done", "เสร็จสิ้น"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        readonly=True,
        copy=False,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้ว่าจ้าง",
        tracking=True,
        states=READONLY_STATES,
    )
    client_org_type = fields.Selection(
        selection=CLIENT_ORG_TYPE_SELECTION,
        string="ประเภทองค์กรผู้ว่าจ้าง",
        tracking=True,
        states=READONLY_STATES,
    )
    leader_name = fields.Char(
        string="หัวหน้าโครงการ",
        tracking=True,
        states=READONLY_STATES,
    )
    faculty_id = fields.Many2one(
        comodel_name="hr.department",
        string="คณะ/หน่วยงาน",
        tracking=True,
        states=READONLY_STATES,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="ภาควิชา/สาขา",
        tracking=True,
        states=READONLY_STATES,
    )
    project_value = fields.Monetary(
        string="มูลค่างาน",
        tracking=True,
        states=READONLY_STATES,
    )
    maintenance_deduction_pct = fields.Float(
        string="% หักค่าบำรุง",
        digits=(5, 2),
        tracking=True,
        states=READONLY_STATES,
    )
    value_after_deduction = fields.Monetary(
        string="มูลค่าหลังหักค่าบำรุง",
        compute="_compute_derived_values",
        store=True,
    )
    equipment_cost = fields.Monetary(
        string="ค่าครุภัณฑ์",
        tracking=True,
        states=READONLY_STATES,
    )
    operating_expense = fields.Monetary(
        string="ค่าดำเนินการ",
        tracking=True,
        states=READONLY_STATES,
    )
    allocatable_value = fields.Monetary(
        string="มูลค่าที่จัดสรรได้",
        compute="_compute_derived_values",
        store=True,
    )
    contract_number = fields.Char(
        string="เลขที่สัญญา",
        tracking=True,
        states=READONLY_STATES,
    )
    date_contract_start = fields.Date(
        string="วันที่เริ่มต้นสัญญา",
        tracking=True,
        states=READONLY_STATES,
    )
    date_contract_end = fields.Date(
        string="วันที่สิ้นสุดสัญญา",
        tracking=True,
        states=READONLY_STATES,
    )
    project_duration = fields.Char(
        string="ระยะเวลาโครงการ",
        tracking=True,
        states=READONLY_STATES,
        help="เช่น '6 เดือน', '1 ปี'",
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
        states=READONLY_STATES,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่ KRIS",
        default=lambda self: self.env.user,
        tracking=True,
        states=READONLY_STATES,
    )
    installment_ids = fields.One2many(
        comodel_name="kris.project.installment",
        inverse_name="project_id",
        string="งวดงาน",
    )
    receipt_ids = fields.One2many(
        comodel_name="kris.project.receipt",
        inverse_name="project_id",
        string="รายรับ",
    )
    allocation_line_ids = fields.One2many(
        comodel_name="kris.project.allocation.line",
        inverse_name="project_id",
        string="การจัดสรรรายได้",
    )
    total_installment_amount = fields.Monetary(
        string="มูลค่าตามงวด (รวม)",
        compute="_compute_totals",
        store=True,
    )
    total_received_amount = fields.Monetary(
        string="รับเงินแล้ว (รวม)",
        compute="_compute_totals",
        store=True,
    )
    revenue_remaining = fields.Monetary(
        string="คงเหลือ",
        compute="_compute_totals",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        tracking=True,
    )

    @api.depends("project_value", "maintenance_deduction_pct", "equipment_cost")
    def _compute_derived_values(self):
        for rec in self:
            rec.value_after_deduction = rec.project_value * (
                1 - rec.maintenance_deduction_pct / 100.0
            )
            rec.allocatable_value = rec.project_value - rec.equipment_cost

    @api.depends(
        "installment_ids.amount",
        "receipt_ids.amount",
        "project_value",
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_installment_amount = sum(rec.installment_ids.mapped("amount"))
            rec.total_received_amount = sum(rec.receipt_ids.mapped("amount"))
            rec.revenue_remaining = rec.project_value - rec.total_received_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("kris.project") or _("New")
                )
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("สามารถยืนยันได้เฉพาะโครงการที่อยู่ในสถานะร่างเท่านั้น"))
        self.write({"state": "confirmed"})

    def action_done(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(_("สามารถปิดได้เฉพาะโครงการที่ยืนยันแล้วเท่านั้น"))
        self.write({"state": "done"})

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("ไม่สามารถยกเลิกโครงการที่เสร็จสิ้นแล้วได้"))
        self.write({"state": "cancel"})

    def action_draft(self):
        for rec in self:
            if rec.state != "cancel":
                raise UserError(_("สามารถรีเซ็ตได้เฉพาะโครงการที่ถูกยกเลิกเท่านั้น"))
        self.write({"state": "draft"})

    def action_compute_allocation(self):
        """Generate or regenerate the 4 standard revenue allocation lines."""
        self.ensure_one()
        ALLOCATION_LINES = [
            (1, "ส่วนกลาง", 35.0),
            (2, "คณะ", 35.0),
            (3, "ภาค", 20.0),
            (4, "KRIS", 10.0),
        ]
        self.allocation_line_ids.unlink()
        self.allocation_line_ids = [
            (0, 0, {"sequence": seq, "name": name, "allocation_pct": pct})
            for seq, name, pct in ALLOCATION_LINES
        ]

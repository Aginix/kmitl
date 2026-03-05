import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

READONLY_STATES = {
    "confirmed": [("readonly", True)],
    "done": [("readonly", True)],
    "cancel": [("readonly", True)],
}

CLIENT_ORG_TYPE_SELECTION = [
    ("government", "หน่วยงานรัฐ"),
    ("state_enterprise", "รัฐวิสาหกิจ"),
    ("private", "เอกชน"),
    ("other", "อื่นๆ"),
]

# Progressive (tiered) deduction brackets: (upper_limit, rate)
_TIERED_BRACKETS = [
    (1_000_000.0, 0.10),
    (5_000_000.0, 0.09),
    (10_000_000.0, 0.08),
    (float("inf"), 0.07),
]


def _compute_tiered_deduction(amount):
    """Return progressive tiered deduction for the given base amount.

    Brackets:
      0 – 1,000,000       → 10 %
      1,000,001 – 5,000,000  → 9 %
      5,000,001 – 10,000,000 → 8 %
      > 10,000,000           → 7 %
    """
    total = 0.0
    prev = 0.0
    for cap, rate in _TIERED_BRACKETS:
        if amount <= prev:
            break
        total += (min(amount, cap) - prev) * rate
        prev = cap
    return total


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
    project_category_id = fields.Many2one(
        comodel_name="kris.project.category",
        string="ประเภทโครงการ",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    project_type_id = fields.Many2one(
        comodel_name="kris.project.type",
        string="ประเภทย่อย",
        required=True,
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
    leader_id = fields.Many2one(
        comodel_name="hr.employee",
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
    # --- Financial fields ---
    project_value = fields.Monetary(
        string="มูลค่างาน",
        tracking=True,
        states=READONLY_STATES,
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
        compute="_compute_allocatable_value",
        store=True,
    )
    maintenance_deduction_type = fields.Selection(
        selection=[
            ("tiered", "ขั้นบันได"),
            ("custom", "กำหนดเอง"),
        ],
        string="วิธีคิดค่าบำรุง",
        default="tiered",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    maintenance_deduction_pct = fields.Float(
        string="% หักค่าบำรุง",
        digits=(5, 2),
        tracking=True,
        states=READONLY_STATES,
    )
    maintenance_deduction_amount = fields.Monetary(
        string="มูลค่าหักค่าบำรุง",
        compute="_compute_maintenance_deduction_amount",
        store=True,
    )
    # --- Allocation template ---
    allocation_template_id = fields.Many2one(
        comodel_name="kris.project.allocation.template",
        string="แม่แบบการจัดสรร",
        states=READONLY_STATES,
    )
    # --- Contract fields ---
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
    # --- One2many ---
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
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="kris_project_attachment_rel",
        column1="project_id",
        column2="attachment_id",
        string="เอกสารแนบ",
    )
    # --- Computed totals ---
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
    total_net_received = fields.Monetary(
        string="ยอดรับสุทธิรวม",
        compute="_compute_totals",
        store=True,
    )
    revenue_remaining = fields.Monetary(
        string="คงเหลือ",
        compute="_compute_totals",
        store=True,
    )
    # --- Standard fields ---
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

    @api.depends("operating_expense")
    def _compute_allocatable_value(self):
        for rec in self:
            rec.allocatable_value = rec.operating_expense

    @api.depends(
        "allocatable_value",
        "maintenance_deduction_type",
        "maintenance_deduction_pct",
    )
    def _compute_maintenance_deduction_amount(self):
        for rec in self:
            if rec.maintenance_deduction_type == "tiered":
                rec.maintenance_deduction_amount = _compute_tiered_deduction(
                    rec.allocatable_value
                )
            else:
                rec.maintenance_deduction_amount = (
                    rec.allocatable_value * rec.maintenance_deduction_pct / 100.0
                )

    @api.depends(
        "installment_ids.amount",
        "receipt_ids.amount",
        "receipt_ids.net_amount",
        "project_value",
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_installment_amount = sum(rec.installment_ids.mapped("amount"))
            rec.total_received_amount = sum(rec.receipt_ids.mapped("amount"))
            rec.total_net_received = sum(rec.receipt_ids.mapped("net_amount"))
            rec.revenue_remaining = rec.project_value - rec.total_received_amount

    @api.onchange("project_value", "equipment_cost")
    def _onchange_operating_expense_suggest(self):
        self.operating_expense = self.project_value - self.equipment_cost

    @api.onchange("project_category_id")
    def _onchange_project_category_id(self):
        if (
            self.project_type_id
            and self.project_type_id.category_id != self.project_category_id
        ):
            self.project_type_id = False

    @api.onchange("faculty_id")
    def _onchange_faculty_id(self):
        if self.department_id and self.department_id.parent_id != self.faculty_id:
            self.department_id = False

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

    def action_add_receipt(self):
        self.ensure_one()
        return {
            "name": "บันทึกรายรับ",
            "type": "ir.actions.act_window",
            "res_model": "kris.project.receipt.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_add_installment(self):
        self.ensure_one()
        return {
            "name": "เพิ่มงวดงาน",
            "type": "ir.actions.act_window",
            "res_model": "kris.project.installment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_apply_allocation_template(self):
        """Apply the selected allocation template to create allocation lines."""
        self.ensure_one()
        if not self.allocation_template_id:
            raise UserError(_("กรุณาเลือกแม่แบบการจัดสรรก่อน"))
        base_amount = self.maintenance_deduction_amount
        self.allocation_line_ids.unlink()
        self.allocation_line_ids = [
            (
                0,
                0,
                {
                    "sequence": tl.sequence,
                    "item_id": tl.item_id.id,
                    "estimated_amount": base_amount * tl.allocation_pct / 100.0,
                },
            )
            for tl in self.allocation_template_id.line_ids
        ]

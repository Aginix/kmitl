from odoo import api, fields, models


class KrisProjectReceiptWizard(models.TransientModel):
    _name = "kris.project.receipt.wizard"
    _description = "KRIS Project Receipt Wizard"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="โครงการ",
        required=True,
        readonly=True,
    )
    available_installment_ids = fields.Many2many(
        comodel_name="kris.project.installment",
        string="งวดที่ใช้ได้",
        compute="_compute_available_installment_ids",
    )
    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="งวดที่",
        domain="[('id', 'in', available_installment_ids)]",
        ondelete="set null",
    )
    name = fields.Char(
        string="เลขที่ใบเสร็จ",
        required=True,
    )
    date = fields.Date(
        string="วันที่รับเงิน",
        required=True,
        default=fields.Date.context_today,
    )
    equipment_cost_in_installment = fields.Monetary(
        string="มูลค่าครุภัณฑ์ในงวด",
        default=0.0,
    )
    amount = fields.Monetary(
        string="จำนวนเงิน",
    )
    net_amount = fields.Monetary(
        string="ยอดรับสุทธิ",
        compute="_compute_net_amount",
    )
    allocate_to_kris = fields.Boolean(
        string="ปันส่วนไป KRIS",
        default=True,
        help="หากเลือก รายรับนี้จะถูกนำไปคำนวณส่วนแบ่งของ KRIS ด้วย",
    )
    note = fields.Text(
        string="หมายเหตุ",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.depends("project_id", "project_id.receipt_ids.installment_id")
    def _compute_available_installment_ids(self):
        for wiz in self:
            used_ids = wiz.project_id.receipt_ids.mapped("installment_id").ids
            available = wiz.project_id.installment_ids.filtered(
                lambda i: i.id not in used_ids
            )
            wiz.available_installment_ids = available

    @api.depends("amount", "equipment_cost_in_installment")
    def _compute_net_amount(self):
        for wiz in self:
            wiz.net_amount = wiz.amount - wiz.equipment_cost_in_installment

    @api.onchange("installment_id")
    def _onchange_installment_id(self):
        if self.installment_id:
            self.amount = self.installment_id.amount

    def action_save(self):
        self.ensure_one()
        self.env["kris.project.receipt"].create(
            {
                "project_id": self.project_id.id,
                "installment_id": self.installment_id.id or False,
                "name": self.name,
                "date": self.date,
                "equipment_cost_in_installment": self.equipment_cost_in_installment,
                "amount": self.amount,
                "allocate_to_kris": self.allocate_to_kris,
                "note": self.note,
            }
        )
        return {"type": "ir.actions.act_window_close"}

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class KrisProjectInstallment(models.Model):
    _name = "kris.project.installment"
    _description = "KRIS Project Installment"
    _order = "sequence, id"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="โครงการ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(
        string="ลำดับ",
        default=10,
    )
    name = fields.Char(
        string="งวดงาน",
        required=True,
    )
    amount = fields.Monetary(
        string="จำนวนเงินที่ได้รับ",
    )
    due_date = fields.Date(
        string="วันครบกำหนด",
    )
    state = fields.Selection(
        selection=[
            ("pending", "รอรับเงิน"),
            ("received", "รับเงินแล้ว"),
        ],
        string="สถานะ",
        default="pending",
    )
    deduction_guarantee = fields.Monetary(
        string="หักเงินประกันผลงาน",
    )
    deduction_advance = fields.Monetary(
        string="หักเงินล่วงหน้า",
    )
    received_from_employer = fields.Monetary(
        string="รับเงินงวดจากผู้ว่าจ้าง",
        compute="_compute_received_from_employer",
        store=True,
    )
    maintenance_fee = fields.Monetary(
        string="ค่าบำรุงสถาบัน",
        compute="_compute_maintenance_fee",
        store=True,
    )
    extra_deduction = fields.Monetary(
        string="หักค่าอื่น ๆ",
    )
    amount_net = fields.Monetary(
        string="จำนวนเงินที่ใช้ได้",
        compute="_compute_amount_net",
        store=True,
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.installment.allocation",
        inverse_name="installment_id",
        string="การจัดสรร",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.depends("amount", "deduction_guarantee", "deduction_advance")
    def _compute_received_from_employer(self):
        for rec in self:
            rec.received_from_employer = (
                rec.amount - rec.deduction_guarantee - rec.deduction_advance
            )

    @api.depends("allocation_ids.amount")
    def _compute_maintenance_fee(self):
        for rec in self:
            rec.maintenance_fee = sum(rec.allocation_ids.mapped("amount"))

    @api.depends("received_from_employer", "maintenance_fee", "extra_deduction")
    def _compute_amount_net(self):
        for rec in self:
            rec.amount_net = (
                rec.received_from_employer - rec.maintenance_fee - rec.extra_deduction
            )

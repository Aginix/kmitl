import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KrisProjectAllocationLine(models.Model):
    _name = "kris.project.allocation.line"
    _description = "KRIS Project Allocation Line"
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
    item_id = fields.Many2one(
        comodel_name="kris.project.allocation.item",
        string="ผู้รับจัดสรร",
        required=True,
    )
    name = fields.Char(
        string="ผู้รับจัดสรร",
        related="item_id.name",
        store=True,
        readonly=True,
    )
    allocation_pct = fields.Float(
        string="% จัดสรร",
        digits=(5, 2),
        compute="_compute_allocation_pct",
        store=True,
    )
    estimated_amount = fields.Monetary(
        string="ประมาณการ (บาท)",
    )
    actual_amount = fields.Monetary(
        string="รับจริง (บาท)",
        compute="_compute_actual_amount",
        store=True,
    )
    installment_allocation_ids = fields.One2many(
        comodel_name="kris.project.installment.allocation",
        inverse_name="allocation_line_id",
        string="การจัดสรรตามงวด",
    )
    receipt_allocation_ids = fields.One2many(
        comodel_name="kris.project.receipt.allocation",
        inverse_name="allocation_line_id",
        string="การจัดสรรตามรายรับ",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.depends("estimated_amount", "project_id.maintenance_deduction_amount")
    def _compute_allocation_pct(self):
        for line in self:
            base = line.project_id.maintenance_deduction_amount
            if base:
                line.allocation_pct = line.estimated_amount / base * 100.0
            else:
                line.allocation_pct = 0.0

    @api.depends("receipt_allocation_ids.amount")
    def _compute_actual_amount(self):
        for line in self:
            line.actual_amount = sum(line.receipt_allocation_ids.mapped("amount"))

    @api.constrains("estimated_amount")
    def _check_estimated_amount_sum(self):
        for line in self:
            base = line.project_id.maintenance_deduction_amount
            if not base:
                continue
            total = sum(line.project_id.allocation_line_ids.mapped("estimated_amount"))
            if total > base + 1e-9:
                raise ValidationError(
                    _(
                        "ผลรวมประมาณการจัดสรรต้องไม่เกินมูลค่าหักค่าบำรุง (%.2f บาท)"
                    )
                    % base
                )

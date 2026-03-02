import logging

from odoo import api, fields, models

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
    name = fields.Char(
        string="ผู้รับจัดสรร",
        required=True,
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

    @api.depends("allocation_pct", "project_id.total_received_amount")
    def _compute_actual_amount(self):
        for line in self:
            line.actual_amount = (
                line.project_id.total_received_amount * line.allocation_pct / 100.0
            )

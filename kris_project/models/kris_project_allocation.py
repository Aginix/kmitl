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

    @api.depends(
        "allocation_pct",
        "project_id.total_net_received",
        "project_id.total_kris_net_received",
        "project_id.maintenance_deduction_amount",
        "project_id.allocatable_value",
    )
    def _compute_actual_amount(self):
        for line in self:
            allocatable = line.project_id.allocatable_value
            if not allocatable:
                line.actual_amount = 0.0
                continue
            # Use the effective maintenance rate (works for both tiered and custom)
            effective_rate = (
                line.project_id.maintenance_deduction_amount / allocatable
            )
            # KRIS only gets a share from receipts flagged for KRIS allocation
            if line.name == "KRIS":
                base = line.project_id.total_kris_net_received * effective_rate
            else:
                base = line.project_id.total_net_received * effective_rate
            line.actual_amount = base * line.allocation_pct / 100.0

    @api.constrains("allocation_pct")
    def _check_allocation_pct_sum(self):
        for line in self:
            sibling_lines = line.project_id.allocation_line_ids
            total_pct = sum(sibling_lines.mapped("allocation_pct"))
            if total_pct > 100.0 + 1e-9:
                raise ValidationError(
                    _(
                        "ผลรวม % จัดสรรต้องไม่เกิน 100%% (ปัจจุบัน: %.2f%%)"
                    )
                    % total_pct
                )

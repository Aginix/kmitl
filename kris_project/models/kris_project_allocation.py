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
    )
    estimated_amount = fields.Monetary(
        string="ประมาณการ (บาท)",
        compute="_compute_amounts",
    )
    actual_amount = fields.Monetary(
        string="รับจริง (บาท)",
        compute="_compute_amounts",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.depends(
        "allocation_pct",
        "project_id.allocatable_value",
        "project_id.total_received_amount",
    )
    def _compute_amounts(self):
        for line in self:
            pct = line.allocation_pct / 100.0
            line.estimated_amount = line.project_id.allocatable_value * pct
            line.actual_amount = line.project_id.total_received_amount * pct

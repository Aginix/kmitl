import logging

from odoo import fields, models

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
        string="งวดที่",
        required=True,
    )
    amount = fields.Monetary(
        string="จำนวนเงิน",
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

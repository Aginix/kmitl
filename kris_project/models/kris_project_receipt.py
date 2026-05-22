import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class KrisProjectReceipt(models.Model):
    _name = "kris.project.receipt"
    _description = "KRIS Project Receipt"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="Installment Number",
        domain="[('project_id', '=', project_id)]",
        ondelete="set null",
    )
    name = fields.Char(
        string="Receipt Number",
        required=True,
        tracking=True,
    )
    date = fields.Date(
        string="Receipt Date",
        required=True,
        tracking=True,
    )
    equipment_cost_in_installment = fields.Monetary(
        string="Equipment Cost in Installment",
        default=0.0,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        tracking=True,
    )
    extra_income = fields.Monetary(
        string="Extra Value",
        default=0.0,
        tracking=True,
    )
    net_amount = fields.Monetary(
        string="Net Amount",
        compute="_compute_net_amount",
        store=True,
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.receipt.allocation",
        inverse_name="receipt_id",
        string="Allocation",
    )
    note = fields.Text(
        string="Note",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.depends("amount", "equipment_cost_in_installment")
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.amount - rec.equipment_cost_in_installment

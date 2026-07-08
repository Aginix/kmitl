import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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
        string="Currency",
        readonly=True,
    )
    project_state = fields.Selection(
        related="project_id.state",
        string="Project State",
    )
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        related="project_id.account_fiscal_year_id",
        store=True,
        index=True,
    )
    project_category_id = fields.Many2one(
        comodel_name="kris.project.category",
        string="Project Category",
        related="project_id.project_category_id",
        store=True,
        index=True,
    )
    project_name = fields.Char(
        string="Project Name",
        related="project_id.project_name",
        store=True,
    )

    def action_delete(self):
        self.ensure_one()
        self.unlink()
        return False

    def unlink(self):
        allocation_lines = self.allocation_ids.mapped("allocation_line_id")
        result = super().unlink()
        if allocation_lines:
            allocation_lines._compute_actual_amount()
        return result

    @api.depends("amount", "equipment_cost_in_installment")
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.amount - rec.equipment_cost_in_installment

    @api.constrains("extra_income", "project_id")
    def _check_extra_income_total(self):
        for rec in self:
            project = rec.project_id
            if not project:
                continue
            total_extra = sum(project.receipt_ids.mapped("extra_income"))
            if total_extra > project.extra_value + 1e-9:
                raise ValidationError(
                    _(
                        "ยอดค่า Extra ที่รับจริงรวมทุกใบ (%.2f บาท) "
                        "เกินจากยอดค่า Extra โครงการ (%.2f บาท)"
                    )
                    % (total_extra, project.extra_value)
                )

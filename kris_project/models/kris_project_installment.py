import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KrisProjectInstallment(models.Model):
    _name = "kris.project.installment"
    _description = "KRIS Project Installment"
    _order = "sequence, id"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    name = fields.Char(
        string="Installment",
        required=True,
    )
    amount = fields.Monetary(
        string="Amount Receive",
    )
    due_date = fields.Date(
        string="Date Due",
    )
    state = fields.Selection(
        selection=[
            ("pending", "รอรับเงิน"),
            ("received", "รับเงินแล้ว"),
        ],
        string="State",
        default="pending",
    )
    deduction_guarantee = fields.Monetary(
        string="Guarantee Deduction",
    )
    deduction_advance = fields.Monetary(
        string="Advance Deduction",
    )
    received_from_employer = fields.Monetary(
        string="Received From Client",
        compute="_compute_received_from_employer",
        store=True,
    )
    maintenance_fee = fields.Monetary(
        string="Maintenance Fee",
        compute="_compute_maintenance_fee",
        store=True,
    )
    extra_deduction = fields.Monetary(
        string="Extra Deduction",
    )
    extra_income = fields.Monetary(
        string="ค่า Extra",
    )
    amount_net = fields.Monetary(
        string="Net Amount",
        compute="_compute_amount_net",
        store=True,
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.installment.allocation",
        inverse_name="installment_id",
        string="Allocation",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project_id = res.get("project_id") or self.env.context.get("default_project_id")
        if project_id and "allocation_ids" in fields_list:
            project = self.env["kris.project"].browse(project_id)
            res["allocation_ids"] = [
                (0, 0, {"allocation_line_id": line.id, "amount": 0.0})
                for line in project.allocation_line_ids
            ]
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence") and vals.get("project_id"):
                project = self.env["kris.project"].browse(vals["project_id"])
                max_seq = max(project.installment_ids.mapped("sequence") or [0])
                vals["sequence"] = max_seq + 10
        return super().create(vals_list)

    @api.depends("amount", "deduction_guarantee", "deduction_advance")
    def _compute_received_from_employer(self):
        for rec in self:
            rec.received_from_employer = (
                rec.amount - rec.deduction_guarantee - rec.deduction_advance
            )

    @api.constrains("extra_income", "project_id")
    def _check_extra_income_total(self):
        for rec in self:
            project = rec.project_id
            if not project:
                continue
            total_extra = sum(project.installment_ids.mapped("extra_income"))
            if total_extra > project.extra_value + 1e-9:
                raise ValidationError(
                    _(
                        "ยอดค่า Extra รวมทุกงวด (%.2f บาท) เกินจากยอดค่า Extra โครงการ (%.2f บาท)"
                    )
                    % (total_extra, project.extra_value)
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

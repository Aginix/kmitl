import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProcurementCommittee(models.Model):
    _name = "procurement.committee"
    _description = "ProcurementComittee"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        ondelete="cascade",
        index=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        ondelete="restrict",
        index=True,
    )
    name = fields.Char(
        string="Committee Name",
        compute="_compute_default_name",
        readonly=False,
        index=True,
    )
    department_id = fields.Many2one(
        related="employee_id.department_id",
    )
    email = fields.Char(
        related="employee_id.work_email",
    )
    phone = fields.Char(
        related="employee_id.work_phone",
    )
    committee_type = fields.Selection(
        selection=[
            ("procurement", "Procurement Committee"),
            ("work_acceptance", "Work Acceptance Committee"),
        ],
    )
    approve_role = fields.Selection(
        selection=[
            ("chairman", "ประธาน"),
            ("committee", "คณะกรรมการ"),
        ],
        string="Role",
        required=True,
    )
    note = fields.Text()

    _sql_constraints = [
        (
            "employee_request_uniq",
            "unique (employee_id,request_id)",
            "Committee has to be unique",
        ),
    ]

    @api.depends("employee_id")
    def _compute_default_name(self):
        for rec in self:
            rec.name = rec.employee_id.display_name if rec.employee_id else ""

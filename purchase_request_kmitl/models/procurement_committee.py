# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProcurementCommittee(models.Model):
    _name = "procurement.committee"
    _description = "Procurement Committee"

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
        compute="_compute_name",
        store=True,
        readonly=False,
        required=True,
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
    mobile_phone = fields.Char(
        string="Mobile Phone",
        related="employee_id.mobile_phone",
        store=False,
        readonly=True,
    )
    committee_type = fields.Selection(
        selection=[
            ("procurement", "Procurement Committee"),
            ("work_acceptance", "Work Acceptance Committee"),
            ("tor_committee", "TOR Committee"),
            ("price_determine", "Price Determine Committee"),
            ("evaluation", "Evaluation Committee"),
            ("work_supervisor", "Work Supervisor"),
        ],
    )
    approve_role = fields.Selection(
        selection=[
            ("chairman", "Chairman"),
            ("committee", "Committee"),
            ("secretary", "Secretary"),
        ],
        string="Role",
        required=True,
        default="committee",
    )
    note = fields.Text()

    _sql_constraints = [
        (
            "employee_request_uniq",
            "unique (employee_id,request_id,committee_type)",
            "Committee member has to be unique within the same committee type.",
        ),
    ]

    @api.depends("employee_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.employee_id.display_name or ""

    @api.constrains("employee_id", "request_id", "committee_type")
    def _check_committee_cross_type_unique(self):
        # TOR, Evaluation and Work Supervisor committees may share members
        allowed_overlap = {"tor_committee", "evaluation", "work_supervisor"}
        for rec in self:
            if not rec.employee_id or not rec.request_id:
                continue
            same_committees = self.env["procurement.committee"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("request_id", "=", rec.request_id.id),
                ]
            )
            types = set(same_committees.mapped("committee_type"))
            if len(types) > 1 and not types.issubset(allowed_overlap):
                raise ValidationError(
                    _(
                        "Employee %s cannot appear in multiple committees "
                        "except TOR, Evaluation, and Work Supervisor committees.",
                        rec.employee_id.name,
                    )
                )

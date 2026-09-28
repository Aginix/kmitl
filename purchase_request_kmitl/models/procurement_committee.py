from odoo import api, fields, models


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
        compute="_compute_default_name",
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
        ondelete={
            "chairman": "set default",
            "committee": "set default",
            "secretary": "set default",
        },
        default="committee",
    )
    note = fields.Text()

    @api.depends("employee_id")
    def _compute_default_name(self):
        for rec in self:
            rec.name = rec.employee_id.display_name if rec.employee_id else ""

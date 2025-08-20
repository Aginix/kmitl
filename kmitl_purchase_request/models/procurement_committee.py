from odoo import api, fields, models


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
        related="employee_id.phone",
    )
    committee_type = fields.Selection(
        selection=[
            ("procurement", "Procurement Committee"),
            ("work_acceptance", "Work Acceptance Committee"),
            ("tor_committee", "TOR Committee"),
            ("price_determine", "Price Determination Committee"),
            ("evaluation", "Evaluation Committee")
        ],
    )
    approve_role = fields.Selection(
        selection=[
            ("chairman", "Chairman"),
            ("committee", "Committee"),
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

    @api.onchange('committee_type')
    def _onchange_committee_type_filter_employee(self):
        self.employee_id = False  # reset เมื่อเปลี่ยน type
        group_map = {
            'procurement': 'kmitl_purchase_request.group_committee_procurement',
            'work_acceptance': 'kmitl_purchase_request.group_committee_work_acceptance',
            'tor_committee': 'kmitl_purchase_request.group_committee_tor',
            'price_determine': 'kmitl_purchase_request.group_committee_price',
            'evaluation': 'kmitl_purchase_request.group_committee_eval',
        }
        group_ref = group_map.get(self.committee_type)
        if group_ref:
            group_id = self.env.ref(group_ref).id
            return {
                'domain': {
                    'employee_id': [('user_id.groups_id', 'in', [group_id])]
                }
            }

from odoo import fields, models


class PurchaseOrderChangeCommitteeSnapshot(models.Model):
    _name = "purchase.order.change.committee.snapshot"
    _description = "Committee Change Snapshot"

    change_id = fields.Many2one(
        comodel_name="purchase.order.change",
        ondelete="cascade",
        required=True,
        index=True,
    )
    committee_type = fields.Selection(
        selection=[
            ("work_acceptance", "Work Acceptance Committee"),
            ("work_supervisor", "Work Supervisor"),
        ],
        required=True,
    )
    snapshot_type = fields.Selection(
        selection=[
            ("before", "Before"),
            ("after", "After"),
        ],
        required=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
    )
    approve_role = fields.Selection(
        selection=[
            ("chairman", "Chairman"),
            ("committee", "Committee"),
            ("secretary", "Secretary"),
        ],
        string="Role",
        required=True,
    )

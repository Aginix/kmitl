from odoo import api, fields, models


class ProcurementCommittee(models.Model):
    _inherit = "procurement.committee"

    committee_type = fields.Selection(
        selection_add=[
            ("tor_committee", "TOR Committee"),
            ("price_determine", "Price Determination Committee"),
            ("evaluation", "Evaluation Committee"),
        ],
    )

    approve_role = fields.Selection(
        selection_add=[
            ("secretary", "Secretary"),
        ],
        required=True,
        ondelete={'chairman': 'set default', 'committee': 'set default', 'secretary': 'set default'},
        default="committee",
    )

    mobile_phone = fields.Char(
        related='employee_id.mobile_phone'
    )

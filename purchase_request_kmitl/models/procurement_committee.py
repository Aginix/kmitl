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


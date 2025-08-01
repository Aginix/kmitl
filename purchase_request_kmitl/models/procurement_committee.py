import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProcurementCommittee(models.Model):
    _inherit = "procurement.committee"

    committee_type = fields.Selection(
        selection_add=[
            ("tor_committee", "TOR Committee"),
            ("price_determine", "Price Determination Committee"),
            ("evaluation", "Evaluation Committee"),
        ],
    )

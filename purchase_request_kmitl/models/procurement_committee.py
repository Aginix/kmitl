import logging

from odoo import api, fields, models

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

    @api.model
    def create(self, vals):
        if not vals.get('name') and vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            vals['name'] = employee.display_name
        return super().create(vals)

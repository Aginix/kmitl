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
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        emp_ids = [vals['employee_id'] for vals in vals_list if vals.get('employee_id') and not vals.get('name')]
        emp_map = {e.id: e.display_name for e in self.env['hr.employee'].browse(emp_ids)}

        for vals in vals_list:
            if not vals.get('name') and vals.get('employee_id') in emp_map:
                vals['name'] = emp_map[vals['employee_id']]

        return super().create(vals_list)


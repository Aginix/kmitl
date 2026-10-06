from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def get_current_fiscal_year_name(self):
        # Server runs in UTC; use the user's local date so the FY flips at local midnight
        fy = self.env.company.find_daterange_fy(fields.Date.context_today(self))
        return fy.name if fy else False

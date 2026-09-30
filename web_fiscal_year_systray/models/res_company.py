from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def get_current_fiscal_year_name(self):
        today = fields.Date.today()
        # Thai fiscal year: Oct 1 – Sep 30; BE year = CE year + 544 when month >= 10
        be_year = today.year + 544 if today.month >= 10 else today.year + 543
        return str(be_year)

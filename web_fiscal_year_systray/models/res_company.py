# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def get_current_fiscal_year_name(self):
        fy = self.env.company.find_daterange_fy(fields.Date.today())
        return fy.name if fy else False

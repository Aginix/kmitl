# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def find_daterange_fy(self, date):
        """
        try to find a date range with type 'fiscalyear'
        with @param:date contained in its date_start/date_end interval
        """
        fiscalyear = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date),
                ("date_to", ">=", date),
            ],
            limit=1,
        )

        return fiscalyear

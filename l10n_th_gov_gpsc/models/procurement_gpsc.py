# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementGpsc(models.Model):
    _name = 'procurement.gpsc'
    _description = 'ProcurementGpsc'

    name = fields.Char(
        required=True,
        string="GPSC Name"
    )

    code = fields.Char(
        required=True,
        string="GPSC Code"
    )

    group_code = fields.Char(
        string="Group Code"
    )

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            domain = [('code', '=', rec.code)]
            count = self.sudo().search_count(domain)
            if count > 1:
                raise ValidationError(_("Code should be unique"))
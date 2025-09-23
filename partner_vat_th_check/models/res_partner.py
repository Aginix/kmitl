# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

from thai_citizen_id import validate

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('vat', 'company_type')
    def _check_thai_citizen_id_for_person(self):
        for record in self:
            if record.company_type == 'person':
                if not validate(record.vat):
                    raise ValidationError("Tax ID Incorrect")
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementGpsc(models.Model):
    _name = 'procurement.gpsc'
    _description = 'ProcurementGpsc'
    _order = 'code'
    _sql_constraints = [
        ('unique_code', 'unique (code)', "Code already exists!"),
    ]
    _rec_names_search = ["name", "code"]

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

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.code}] {rec.name}"
            result.append((rec.id, name))
        return result
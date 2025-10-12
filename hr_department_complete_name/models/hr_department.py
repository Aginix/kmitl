# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = "hr.department"

    def name_get(self):
        res = []
        for rec in self:
            name = rec.complete_name
            if rec.code:
                name = ("[%(code)s] %(name)s") % {"code": rec.code, "name": name}
            res.append((rec.id, name))
        return res

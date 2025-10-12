# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    complete_name = fields.Char(
        compute="_compute_complete_name", recursive=True, store=True
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = _("%(parent)s %(own)s") % {
                    "parent": rec.parent_id.complete_name,
                    "own": rec.name,
                }
            else:
                rec.complete_name = rec.name

    def name_get(self):
        res = []
        for rec in self:
            name = rec.complete_name
            if rec.code:
                name = ("[%(code)s] %(name)s") % {"code": rec.code, "name": name}
            res.append((rec.id, name))
        return res

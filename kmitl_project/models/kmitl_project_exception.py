# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _name = "kmitl.project"
    _order = "main_exception_id asc, id desc"
    _inherit = ["kmitl.project", "base.exception"]

    def action_project_draft(self):
        res = super().action_project_draft()
        for request in self:
            request.exception_ids = False
            request.main_exception_id = False
            request.ignore_exception = False
        return res

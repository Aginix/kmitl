# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseWorkAcceptanceAttachment(models.TransientModel):
    _name = 'purchase.work.acceptance.attachment'
    _description = 'PurchaseWorkAcceptanceAttachment'

    name = fields.Char('Name')

    wizard_id = fields.Many2one("work.accepted.date.wizard", string="Wizard")
    wa_id  = fields.Many2one("work.acceptance", string="Work Acceptance")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")


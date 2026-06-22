# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    notification_type = fields.Selection(
        selection_add=[('email_inbox', "Handle by Emails and Odoo")],
        ondelete={'email_inbox': 'set inbox'}
    )

# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def name_get(self):
        return super().name_get()
        # res = []
        # for user in self:
        #     # name = user.name_get()
        #     name = "Hello, World. I'm from Thailand.... " + "\n" + "email: nonpawit.tee@gmail.com" + "\n" + "Thailand" + "\n" + "Nonthaburi"
        #     res.append((user.id, name))
        # return res

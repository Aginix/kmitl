# -*- coding: utf-8 -*-
from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _partner_autocomplete_type(self):
        # Put the KMITL partner type on the autocomplete badge in place of the
        # generic Individual/Company label; fall back to it when a contact has
        # no type set yet.
        self.ensure_one()
        if self.partner_type_id:
            return self.partner_type_id.name
        return super()._partner_autocomplete_type()

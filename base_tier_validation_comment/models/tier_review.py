# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TierReview(models.Model):
    _inherit = 'tier.review'

    has_approve_comment = fields.Boolean(related="definition_id.has_approve_comment", readonly=True)
    has_reject_comment = fields.Boolean(related="definition_id.has_reject_comment", readonly=True)

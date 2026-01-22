# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = 'purchase.order.change.wizard'
    _description = _('Purchase Order ChangeWizard')



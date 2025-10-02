# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseCommitteeChangeset(models.Model):
    _name = 'purchase.committee.changeset'

    changeset_id = fields.Many2one(
        comodel_name="changeset",
        string="changeset",
        ondelete="cascade",
        index=True,
    )
    partner_ref = fields.Char('Vendor Reference', copy=False,
        help="Reference of the sales order or bid sent by the vendor. "
             "It's used to do the matching when you receive the "
             "products as this reference is usually written on the "
             "delivery order sent by your vendor.")

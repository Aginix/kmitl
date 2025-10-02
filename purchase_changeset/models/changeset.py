# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Changeset(models.Model):
    _name = 'changeset'
    _description = 'Changeset'

    name = fields.Char('ชื่อเรื่อง')
    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Request",
        ondelete="cascade",
        index=True,
    )
    purchase_partner_ref = fields.Char(
        string="ข้อมูลปัจุบัน",
        store=True,
    )
    purchase_changeset_committee_id = fields.Many2one(
        comodel_name="purchase.committee.changeset",
        string="Purchase changeset Committees",
        copy=True,
    )
    committee_partner_ref = fields.Char(
        string="ข้อมูลก่อนหน้า",
        related="purchase_changeset_committee_id.partner_ref",
        store=True,
    )
    wizard_id = fields.One2many(
        comodel_name="purchase.committee.changeset",
        inverse_name="changeset_id",
        string="Wizard",
    )

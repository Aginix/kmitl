# -*- coding: utf-8 -*-
# Copyright (C) 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentGuaranteeType(models.Model):
    _name = "account.payment.guarantee.type"
    _description = "Account Payment Guarantee Type"
    _order = "sequence, name"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
        help="Name of the guarantee type"
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order of display"
    )
    description = fields.Text(
        string="Description",
        translate=True,
        help="Detailed description of the guarantee type"
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Uncheck to archive the guarantee type"
    )
    color = fields.Integer(
        string="Color",
        help="Color for display in kanban and other views"
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        index=True,
        ondelete="restrict",
        help="Account to be used for this guarantee type in accounting entries"
    )


    def name_get(self):
        return [(record.id, record.name) for record in self]

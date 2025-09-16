# -*- coding: utf-8 -*-
# Copyright (C) 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_guarantee_payment = fields.Boolean(
        string="Guarantee Payment",
        help="Indicates if this payment is related to guarantee transactions",
        store=True,
        readonly=False,
    )

    guarantee_type_id = fields.Many2one(
        comodel_name="account.payment.guarantee.type",
        string="Guarantee Type",
        help="Type of guarantee transaction",
        store=True,
        readonly=False,
    )

    def _get_trigger_fields_to_synchronize(self):
        return (
            *super()._get_trigger_fields_to_synchronize(),
            'is_guarantee_payment',
            'guarantee_type_id'
        )

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Override to use guarantee type account when applicable."""
        # Get standard payment lines from parent method
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)

        # Apply guarantee account logic if guarantee type has an account specified
        if self.is_guarantee_payment and self.guarantee_type_id.account_id:
            editing_val = line_vals_list[1]
            editing_val['account_id'] = self.guarantee_type_id.account_id.id

        return line_vals_list

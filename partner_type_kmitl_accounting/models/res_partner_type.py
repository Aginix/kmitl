# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError

from .res_partner import _PARTNER_TYPE_ACCOUNT_FIELDS


class ResPartnerType(models.Model):
    _inherit = 'res.partner.type'

    property_account_receivable_id = fields.Many2one(
        comodel_name='account.account', string='Account Receivable',
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        company_dependent=True, tracking=True,
        help='This account will be used instead of the default one as the receivable account for the partner',
    )
    property_account_payable_id = fields.Many2one(
        comodel_name='account.account', string='Account Payable',
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        company_dependent=True, tracking=True,
        help='This account will be used instead of the default one as the payable account for the partner',
    )
    wht_tax_id = fields.Many2one(
        comodel_name='account.withholding.tax', string='WHT',
        company_dependent=True, tracking=True,
    )

    def action_apply_accounts_to_partners(self):
        """Stamp this type's accounts onto all of its partners (incl. archived).

        Deliberately per-record: the confirm dialog is phrased about one type,
        and a multi-record version would be the rejected auto-cascade in a
        different costume.
        """
        self.ensure_one()
        if not any(self[f] for f in _PARTNER_TYPE_ACCOUNT_FIELDS):
            raise UserError(_("No account is configured on this partner type."))

        # Use active_test=False so archived partners get updated too; once
        # restored they must carry the current accounts, not stale ones.
        partners = self.env['res.partner'].with_context(active_test=False).search(
            [('partner_type_id', '=', self.id)]
        )

        if not partners:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("No partner uses this type yet."),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        updated = partners._apply_partner_type_accounts()
        total = len(partners)
        n_updated = len(updated)

        if not n_updated:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "All %(total)s partner(s) already use these accounts."
                    ) % {'total': total},
                    'type': 'warning',
                    'sticky': False,
                },
            }

        message = _("%(updated)s of %(total)s partner(s) updated.") % {
            'updated': n_updated,
            'total': total,
        }
        # Partner-side fields are untracked, so this is the only audit trail
        # for a mass rewrite. The type already tracks who changed the accounts,
        # closing the loop.
        self.message_post(body=message)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

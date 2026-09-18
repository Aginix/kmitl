# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Backfill ``partner_type_id`` on every pre-existing ``res.partner``.

    The form makes ``partner_type_id`` required, so any partner that
    predates this module would fail to save on its first edit otherwise.
    """
    # tracking_disable: partner_type_id is tracked, so a mass write would post
    # one chatter note per partner on an existing database.
    env = api.Environment(cr, SUPERUSER_ID, {'tracking_disable': True})
    type_company = env.ref('partner_type_kmitl.partner_type_company', raise_if_not_found=False)
    type_other = env.ref('partner_type_kmitl.partner_type_other', raise_if_not_found=False)
    if not type_company or not type_other:
        return
    partners = env['res.partner'].with_context(active_test=False).search(
        [('partner_type_id', '=', False)]
    )
    company_partners = partners.filtered(lambda p: p.is_company)
    (partners - company_partners).write({'partner_type_id': type_other.id})
    company_partners.write({'partner_type_id': type_company.id})

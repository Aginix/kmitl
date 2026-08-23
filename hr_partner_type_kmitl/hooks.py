# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Classify the work contact of every pre-existing employee as staff.

    The ``base.automation`` in ``data/`` only fires ``on_create``, so employees
    that predate this module would keep the ``partner_type_other`` default that
    ``partner_type_kmitl``'s own backfill gave them — leaving no partner at all
    typed as ``partner_type_employee``.
    """
    # tracking_disable: partner_type_id is tracked, so a mass write would post
    # one chatter note per work contact.
    env = api.Environment(cr, SUPERUSER_ID, {'tracking_disable': True})
    employee_type = env.ref(
        'partner_type_kmitl.partner_type_employee', raise_if_not_found=False
    )
    if not employee_type:
        return
    employees = env['hr.employee'].with_context(active_test=False).search(
        [('work_contact_id', '!=', False)]
    )
    employees.work_contact_id.write({'partner_type_id': employee_type.id})

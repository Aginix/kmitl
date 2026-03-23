from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env.ref(
        'purchase_work_acceptance.group_enable_wa_on_po',
        raise_if_not_found=False
    )
    if group:
        settings = env['res.config.settings'].create({
            'group_enable_wa_on_po': True
        })
        settings.execute()

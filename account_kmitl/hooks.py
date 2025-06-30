from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("account_kmitl.chart")._load(env.ref("base.main_company"))

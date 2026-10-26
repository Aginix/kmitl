from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["sarabun.verb"]._seed_todo_category()

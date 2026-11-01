from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Seed every existing verb's Todo category on its new per-verb activity type
    (ADR-0020) — agx_sarabun's own migration has created those types already.
    Admin-made verbs too, so their Todos keep the category the old discriminator
    gave them."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["sarabun.verb"]._seed_todo_category()

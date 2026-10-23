from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Seed the built-in verbs' Todo category on their new per-verb activity types
    (ADR-0020) — agx_sarabun's own migration has created those types already."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["sarabun.verb"]._seed_builtin_todo_category()

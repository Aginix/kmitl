from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Subscribe the owners of every project to its existing หนังสือ — only the
    sender and the reached users could open it before."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    documents = env["sarabun.document"].search([("origin_model", "=", "kmitl.project")])
    env["kmitl.project"].browse(
        set(documents.mapped("origin_res_id"))
    ).exists()._sync_sarabun_owner_followers()

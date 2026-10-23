from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Backfill ``sarabun_document_number`` from the หนังสือ already numbered
    before this version (the newest numbered letter per transfer wins)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    documents = env["sarabun.document"].search(
        [
            ("origin_model", "=", "budget.transfer"),
            ("register_number_id", "!=", False),
        ],
        order="id",
    )
    Transfer = env["budget.transfer"]
    for document in documents:
        transfer = Transfer.browse(document.origin_res_id).exists()
        if transfer:
            transfer.sarabun_document_number = document.name

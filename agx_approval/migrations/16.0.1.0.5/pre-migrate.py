def migrate(cr, version):
    cr.execute(
        "DELETE FROM approval_request_payee WHERE partner_id IS NULL"
    )

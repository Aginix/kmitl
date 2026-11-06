from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The debt now starts at the paid confirmation (ADR-0034): start the
    loans whose voucher was confirmed paid but is still waiting to be
    posted."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    payments = env["account.payment"].search(
        [
            ("advance_payment_id.state", "=", "approved"),
            ("finance_state", "=", "paid"),
            ("state", "!=", "cancel"),
        ]
    )
    for payment in payments:
        payment.advance_payment_id.action_start(payment=payment)

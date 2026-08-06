import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Move unposted cheque payments onto the เช็ค payment method.

    account_kmitl retires Odoo's stock Manual method and moves the payments
    that were on it to their journal's first KMITL method (เงินโอน). It cannot
    tell a cheque from a transfer — ``kmitl.payment.type.is_cheque`` belongs to
    this module — so the cheques are corrected here, once account_kmitl's own
    migration has run (module upgrades follow the dependency order).

    Writing the method line does not rebuild the journal entry
    (``payment_method_line_id`` is deliberately not a synchronisation trigger),
    so withholding-tax write-off lines are preserved.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    payments = env["account.payment"].search(
        [
            ("kmitl_payment_type_id.is_cheque", "=", True),
            ("move_id.state", "not in", ("posted", "cancel")),
        ]
    )
    moved = env["account.payment"]
    for payment in payments:
        line = payment.journal_id._kmitl_cheque_method_line(
            payment.payment_type
        )
        if line and payment.payment_method_line_id != line:
            payment.payment_method_line_id = line.id
            moved |= payment
    if moved:
        _logger.info(
            "finance_kmitl: moved %d cheque payment(s) onto the เช็ค payment "
            "method.",
            len(moved),
        )

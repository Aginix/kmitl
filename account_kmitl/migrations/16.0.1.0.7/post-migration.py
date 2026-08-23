import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import (
    _kmitl_payment_journals,
    _setup_payment_method_lines,
)

_logger = logging.getLogger(__name__)


def _repoint_unposted_payments(env, company):
    """Move payments still on a detached method (the removed Manual lines) onto
    their journal's first KMITL method (เงินโอน on a bank journal).

    Only payments that are not posted yet are touched: a posted payment keeps
    the method it was actually booked with (core ``unlink`` detaches such lines
    from the journal instead of deleting them, so the history stays readable).
    Modules that know a payment is settled differently correct it afterwards —
    finance_kmitl moves its cheque payments onto the เช็ค method.
    """
    journals = _kmitl_payment_journals(env, company)
    payments = env["account.payment"].search(
        [
            ("journal_id", "in", journals.ids),
            ("move_id.state", "not in", ("posted", "cancel")),
            ("payment_method_line_id.journal_id", "=", False),
        ]
    )
    for payment in payments:
        line = payment.journal_id._get_available_payment_method_lines(
            payment.payment_type
        )[:1]
        if line:
            payment.payment_method_line_id = line.id
    if payments:
        _logger.info(
            "account_kmitl: repointed %d unposted payment(s) to the KMITL "
            "payment methods.",
            len(payments),
        )


def migrate(cr, version):
    """Offer the KMITL payment methods on existing databases and retire Manual.

    ``post_init_hook`` only runs on install. The method records themselves are
    created by ``data/account_payment_method.xml`` during this upgrade (which
    auto-adds lines to the journals existing at that moment); this pass makes
    sure every bank/cash journal carries them, applies the payment-account
    convention, removes Odoo's stock Manual lines, and moves the payments that
    were still on them.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")
    _setup_payment_method_lines(env, company)
    _repoint_unposted_payments(env, company)

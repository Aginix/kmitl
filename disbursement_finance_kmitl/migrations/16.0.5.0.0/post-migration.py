# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Re-word the finance office's Todo, which the upgrade will not touch.

    The activity types live in a ``noupdate="1"`` data file — deliberately, so an
    office that renamed one keeps its name — so the new summary would never reach
    a database that already has the record. Since the authorisation now raises the
    vouchers, the old wording ("create the payment and send it to the bank") asks
    for work that is already done, so it is written across by hand.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    activity = env.ref(
        "disbursement_finance_kmitl.mail_activity_dr_to_pay",
        raise_if_not_found=False,
    )
    if not activity:
        _logger.warning("mail_activity_dr_to_pay is missing; nothing to re-word.")
        return
    activity.summary = (
        "A disbursement request was authorized and its vouchers are ready — "
        "put them in an e-payment file and confirm the payment"
    )

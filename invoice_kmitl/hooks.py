# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, api, fields

# Fiscal years numbered ahead of time, the current one included.
SEEDED_FISCAL_YEARS = 5


def post_init_hook(cr, registry):
    """Create the numbering sequences of the coming fiscal years up front.

    ``ir.sequence.code`` is not unique, so a sequence created on first use can be
    created twice when two documents are the first of their fiscal year and are
    saved at the same moment: both then number themselves 0001.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    today = fields.Date.context_today(env["kmitl.invoice"])
    for model in ("kmitl.invoice", "kmitl.invoice.submission"):
        for years in range(SEEDED_FISCAL_YEARS):
            env[model]._get_sequence(today + relativedelta(years=years))

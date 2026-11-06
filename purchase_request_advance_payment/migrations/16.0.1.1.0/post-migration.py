from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The one-loan-per-request rule is gone with its flag, and the payment
    method rule now ships off. Both are noupdate, so the data file cannot
    change an installed database."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = "purchase_request_advance_payment"
    single = env.ref(f"{module}.excep_pr_single_loan", raise_if_not_found=False)
    if single:
        single.unlink()
    not_advance = env.ref(f"{module}.excep_pr_not_advance", raise_if_not_found=False)
    if not_advance:
        not_advance.active = False

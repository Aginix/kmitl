from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import _setup_payment_method_lines


def migrate(cr, version):
    """Offer the KMITL payment methods on existing databases.

    ``post_init_hook`` only runs on install. The method records themselves are
    created by ``data/account_payment_method.xml`` during this upgrade (which
    auto-adds lines to the bank journals existing at that moment); this pass
    ensures the KMITL journals carry all the lines and applies the
    payment-account convention to lines created without one.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")
    _setup_payment_method_lines(env, company)

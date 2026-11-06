from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Both numbers run per fiscal year, with a four-digit BE year (ADR-0035).
    The sequences are noupdate, so the data file cannot change them."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, prefix in (
        ("advance_payment.seq_advance_payment_agreement", "ADV/%(year_be)s/"),
        ("advance_payment.seq_advance_payment_contract", "APC/%(year_be)s/"),
    ):
        sequence = env.ref(xmlid, raise_if_not_found=False)
        if sequence:
            sequence.write({"prefix": prefix, "use_date_range": True})

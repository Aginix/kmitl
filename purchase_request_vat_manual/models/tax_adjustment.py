from odoo.tools.misc import formatLang


def apply_tax_adjustment(env, tax_totals, delta, amount_total, currency):
    """Shift the first tax group of a ``tax_totals`` dict by ``delta`` and
    align its grand total with ``amount_total``. Returns the same dict."""
    groups = [g for gs in tax_totals["groups_by_subtotal"].values() for g in gs]
    if not groups or currency.is_zero(delta):
        return tax_totals
    group = groups[0]
    group["tax_group_amount"] += delta
    group["formatted_tax_group_amount"] = formatLang(
        env, group["tax_group_amount"], currency_obj=currency
    )
    tax_totals["amount_total"] = amount_total
    tax_totals["formatted_amount_total"] = formatLang(
        env, amount_total, currency_obj=currency
    )
    return tax_totals

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """excep_missing_manager is noupdate: re-apply its route-aware check so
    an Office-route request (no Endorse step, ADR-0027) is not blocked for a
    missing supervisor."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        "advance_payment_exception.excep_missing_manager", raise_if_not_found=False
    )
    if rule:
        rule.write(
            {
                "exception_type": "by_py_code",
                "domain": False,
                "code": "if self.state in ('draft', 'to_endorse') and not"
                " self.endorser_id and 'to_endorse' in self._get_route_states():\n"
                "    failed = True",
            }
        )

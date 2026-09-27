import logging

_logger = logging.getLogger(__name__)

# ADR-0016 (pools never nest). The new engine treats a reservation's control node
# as the single funded coordinate covering it on every axis, and the guard blocks
# posting a move/transfer that would create two comparable (nested) pools. Data
# posted before the guard may already contain nested pools. This upgrade does NOT
# rewrite that data — it only reports the overlaps so they can be resolved before
# they surface as a warning at reserve time. Run against every open fiscal year.


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    controller = env["budget.controller"]
    fiscal_years = env["account.fiscal.year"].search([])
    total = 0
    for fy in fiscal_years:
        pairs = controller.scan_pool_overlaps(fy.id, fy.company_id.id)
        if not pairs:
            continue
        total += len(pairs)
        _logger.warning(
            "ADR-0016 pool-nesting scan: fiscal year %s has %d nested pool "
            "pair(s):", fy.display_name, len(pairs)
        )
        for coord_a, coord_b in pairs:
            _logger.warning(
                "  nested pools: [%s] <-> [%s]",
                controller._coord_label(coord_a),
                controller._coord_label(coord_b),
            )
    if not total:
        _logger.info("ADR-0016 pool-nesting scan: no nested pools found.")

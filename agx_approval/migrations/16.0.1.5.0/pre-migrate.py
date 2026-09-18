# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """budget_selection_mode dropped 'chart' (reserve-new) and 'reservation'
    (draw-any-existing) in favour of 'normal' (base) + bridge-added modes.
    Behaviour-neutral: the field is a UI affordance — the server keys
    draw-down off ``reservation_commitment_id``, never off this field — so
    remapping every existing value to 'normal' changes nothing except which
    radio option a resumed form shows."""
    if not version:
        return
    cr.execute(
        "UPDATE approval_request SET budget_selection_mode = 'normal' "
        "WHERE budget_selection_mode IN ('chart', 'reservation')"
    )
    _logger.info(
        "agx_approval budget_selection_mode: remapped %s rows to 'normal'",
        cr.rowcount,
    )

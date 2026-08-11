# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """ADR-0005 lifecycle overhaul removed the ``new`` and ``on_hold`` states.
    Remap existing kmitl.project records before the new Selection loads:

      new     -> in_progress  (was confirmed + budget reserved + ready to run;
                               in_progress is the approved-and-executing state
                               that likewise carries a live reservation)
      on_hold -> draft        (on_hold was only reachable pre-execution and had
                               released its reservation, so it maps to an
                               un-reserved, re-editable draft)

    NOTE: the on_hold mapping is a policy choice — switch the target to 'cancel'
    if held projects should be treated as abandoned rather than restartable.
    """
    if not version:
        return
    cr.execute("UPDATE kmitl_project SET state = 'in_progress' WHERE state = 'new'")
    _logger.info(
        "kmitl_project ADR-0005: remapped %s 'new' -> 'in_progress'", cr.rowcount
    )
    cr.execute("UPDATE kmitl_project SET state = 'draft' WHERE state = 'on_hold'")
    _logger.info(
        "kmitl_project ADR-0005: remapped %s 'on_hold' -> 'draft'", cr.rowcount
    )

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Start the two-approver sub-workflow for in-flight verified requests.

    Requests already sitting at ``verified`` predate the two-approver step and
    default to ``approval_state = 'none'``, which would leave them with no
    approve button. Move them to the Finance Director step so approval can
    proceed. (Todos are scheduled by the workflow transitions, not here.)
    """
    cr.execute(
        """
        UPDATE disbursement_request
        SET approval_state = 'pending_finance'
        WHERE state = 'verified'
          AND (approval_state IS NULL OR approval_state = 'none')
        """
    )
    _logger.info(
        "disbursement: moved %s verified request(s) to pending_finance",
        cr.rowcount,
    )

"""Migrate legacy purchase.request state values to the split post-Sarabun states.

See docs/adr/0005-post-sarabun-state-split.md.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Case 1: approved + is_egp + no PA -> in_egp (fill egp_status='waiting' if null)
    cr.execute(
        """
        UPDATE purchase_request pr
           SET state = 'in_egp',
               egp_status = COALESCE(egp_status, 'waiting')
         WHERE pr.state = 'approved'
           AND pr.is_egp IS TRUE
           AND NOT EXISTS (
               SELECT 1 FROM purchase_request_approval pa
                WHERE pa.request_id = pr.id
           )
        """
    )
    _logger.info("post-migration: case 1 (approved+is_egp) updated %s rows", cr.rowcount)

    # Case 2: approved + not is_egp + has PA -> in_approval
    cr.execute(
        """
        UPDATE purchase_request pr
           SET state = 'in_approval'
         WHERE pr.state = 'approved'
           AND (pr.is_egp IS NOT TRUE)
           AND EXISTS (
               SELECT 1 FROM purchase_request_approval pa
                WHERE pa.request_id = pr.id
           )
        """
    )
    _logger.info("post-migration: case 2 (approved+non-egp+has PA) updated %s rows", cr.rowcount)

    # Case 3: approved + not is_egp + no PA -> leave alone; log the IDs for ops.
    cr.execute(
        """
        SELECT id, name
          FROM purchase_request
         WHERE state = 'approved'
           AND (is_egp IS NOT TRUE)
           AND NOT EXISTS (
               SELECT 1 FROM purchase_request_approval pa
                WHERE pa.request_id = purchase_request.id
           )
        """
    )
    residual = cr.fetchall()
    if residual:
        _logger.warning(
            "post-migration: case 3 (approved+non-egp+no PA) left %s rows in 'approved'; "
            "ops must trigger PA creation manually. IDs: %s",
            len(residual),
            [(rid, name) for rid, name in residual],
        )

    # Case 4 (safety net): any records that ran an intermediate ADR-0005 build
    # were parked at 'in_purchase'; drawio v2 reuses OCA base 'in_progress' instead.
    cr.execute(
        """
        UPDATE purchase_request
           SET state = 'in_progress'
         WHERE state = 'in_purchase'
        """
    )
    _logger.info("post-migration: case 4 (in_purchase safety-net) updated %s rows", cr.rowcount)

    # Case 5: PA state reduction (5 -> 4 states).
    # Merge legacy 'validate' into 'to_approve'; rename 'rejected' to 'cancel'.
    cr.execute(
        """
        UPDATE purchase_request_approval
           SET state = 'to_approve'
         WHERE state = 'validate'
        """
    )
    _logger.info("post-migration: case 5a (PA validate -> to_approve) updated %s rows", cr.rowcount)

    cr.execute(
        """
        UPDATE purchase_request_approval
           SET state = 'cancel'
         WHERE state = 'rejected'
        """
    )
    _logger.info("post-migration: case 5b (PA rejected -> cancel) updated %s rows", cr.rowcount)

    # Case 6 (safety net): any records that ran round-3 build parked at 'cancelled';
    # round-4 aligns with upstream and uses 'cancel'.
    cr.execute(
        """
        UPDATE purchase_request
           SET state = 'cancel'
         WHERE state = 'cancelled'
        """
    )
    _logger.info("post-migration: case 6a (PR cancelled safety-net) updated %s rows", cr.rowcount)

    cr.execute(
        """
        UPDATE purchase_request_approval
           SET state = 'cancel'
         WHERE state = 'cancelled'
        """
    )
    _logger.info("post-migration: case 6b (PA cancelled safety-net) updated %s rows", cr.rowcount)

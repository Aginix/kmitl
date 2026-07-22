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

    # Case 4: PA state reduction (5 -> 4 states).
    # Merge legacy 'validate' into 'to_approve'; remap legacy 'rejected'
    # (cancel-like semantic per ADR-0005) to the new past-tense 'cancelled'.
    cr.execute(
        """
        UPDATE purchase_request_approval
           SET state = 'to_approve'
         WHERE state = 'validate'
        """
    )
    _logger.info("post-migration: case 4a (PA validate -> to_approve) updated %s rows", cr.rowcount)

    cr.execute(
        """
        UPDATE purchase_request_approval
           SET state = 'cancelled'
         WHERE state = 'rejected'
        """
    )
    _logger.info("post-migration: case 4b (PA rejected -> cancelled) updated %s rows", cr.rowcount)

    # Case 5: PR terminal state rename to past-tense — 'cancel' -> 'cancelled'.
    # 'cancel' has existed on PR since 16.0 via purchase_request_kmitl.selection_add.
    cr.execute(
        """
        UPDATE purchase_request
           SET state = 'cancelled'
         WHERE state = 'cancel'
        """
    )
    _logger.info("post-migration: case 5 (PR cancel -> cancelled) updated %s rows", cr.rowcount)

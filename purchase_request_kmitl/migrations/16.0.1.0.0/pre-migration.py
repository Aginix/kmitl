import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Map obsolete purchase.request state values to new 11-state machine.

    Old states → new states:
      draft        → draft        (no change)
      to_examine   → confirm      (was: pre-verification step)
      to_verify    → confirm      (was: pending requester confirmation)
      to_approve   (with sarabun document) → to_approve  (no change)
      to_approve   (no sarabun document)   → to_submit   (was submitted but no sarabun yet)
      approved     (has PO)                → done
      approved     (has approved PA)       → purchasing
      approved     (has non-approved PA)   → in_pa
      approved     (is_egp + egp_status='in_progress') → purchasing
      approved     (is_egp)               → egp
      approved     (default)              → approved
      in_progress  (has PO)               → done
      in_progress  (has approved PA)      → purchasing
      in_progress  (has non-approved PA)  → in_pa
      in_progress  (is_egp + egp_status='in_progress') → purchasing
      in_progress  (default)              → purchasing
      done         → done        (no change)
      rejected     → cancel
    """
    _logger.info("pre-migration: remapping purchase.request states")

    # 1. rejected → cancel
    cr.execute(
        "UPDATE purchase_request SET state = 'cancel' WHERE state = 'rejected'"
    )
    _logger.info("migrated %d rejected → cancel", cr.rowcount)

    # 2. to_examine → confirm
    cr.execute(
        "UPDATE purchase_request SET state = 'confirm' WHERE state = 'to_examine'"
    )
    _logger.info("migrated %d to_examine → confirm", cr.rowcount)

    # 3. to_verify → confirm
    cr.execute(
        "UPDATE purchase_request SET state = 'confirm' WHERE state = 'to_verify'"
    )
    _logger.info("migrated %d to_verify → confirm", cr.rowcount)

    # 4. to_approve without sarabun document → to_submit
    cr.execute(
        """
        UPDATE purchase_request
        SET state = 'to_submit'
        WHERE state = 'to_approve'
          AND (main_sarabun_document_id IS NULL)
        """
    )
    _logger.info("migrated %d to_approve (no sarabun) → to_submit", cr.rowcount)
    # remaining to_approve (with sarabun) stay as to_approve (no change needed)

    # 5. approved/in_progress with PO → done
    cr.execute(
        """
        UPDATE purchase_request pr
        SET state = 'done'
        WHERE pr.state IN ('approved', 'in_progress')
          AND EXISTS (
              SELECT 1 FROM purchase_order po
              WHERE po.purchase_request_id = pr.id
                AND po.state NOT IN ('cancel', 'draft')
          )
        """
    )
    _logger.info("migrated approved/in_progress (has PO) → done: %d", cr.rowcount)

    # 6. approved/in_progress with egp_status='in_progress' → purchasing
    cr.execute(
        """
        UPDATE purchase_request
        SET state = 'purchasing'
        WHERE state IN ('approved', 'in_progress')
          AND egp_status = 'in_progress'
        """
    )
    _logger.info(
        "migrated approved/in_progress (egp in_progress) → purchasing: %d", cr.rowcount
    )

    # 7. approved/in_progress with approved PA → purchasing
    cr.execute(
        """
        UPDATE purchase_request pr
        SET state = 'purchasing'
        WHERE pr.state IN ('approved', 'in_progress')
          AND EXISTS (
              SELECT 1 FROM purchase_request_approval pra
              WHERE pra.request_id = pr.id AND pra.state = 'approved'
          )
        """
    )
    _logger.info(
        "migrated approved/in_progress (PA approved) → purchasing: %d", cr.rowcount
    )

    # 8. approved/in_progress with non-approved PA → in_pa
    cr.execute(
        """
        UPDATE purchase_request pr
        SET state = 'in_pa'
        WHERE pr.state IN ('approved', 'in_progress')
          AND EXISTS (
              SELECT 1 FROM purchase_request_approval pra
              WHERE pra.request_id = pr.id AND pra.state != 'approved'
          )
        """
    )
    _logger.info(
        "migrated approved/in_progress (PA not approved) → in_pa: %d", cr.rowcount
    )

    # 9. approved/in_progress with is_egp (waiting) → egp
    cr.execute(
        """
        UPDATE purchase_request
        SET state = 'egp'
        WHERE state IN ('approved', 'in_progress')
          AND is_egp = true
          AND (egp_status = 'waiting' OR egp_status IS NULL)
        """
    )
    _logger.info(
        "migrated approved/in_progress (is_egp waiting) → egp: %d", cr.rowcount
    )

    # 10. remaining in_progress → purchasing
    cr.execute(
        "UPDATE purchase_request SET state = 'purchasing' WHERE state = 'in_progress'"
    )
    _logger.info("migrated remaining in_progress → purchasing: %d", cr.rowcount)

    # 11. remaining approved → approved (no change, already correct)

    _logger.info("pre-migration: purchase.request state remapping complete")

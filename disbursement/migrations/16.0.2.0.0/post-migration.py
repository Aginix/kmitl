# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration for the "pay by name list" (multi-partner only) rework.

Disbursement requests no longer offer a single/multi partner choice: every
request now pays a name list, so the recipient lives on each line. This script
brings existing records in line with the new model:

- force ``partner_type`` to ``multi`` on every request;
- backfill any line still missing a partner from the old single-partner
  header partner, so the now-unconditional line partner constraint holds;
- default the new ``payment_type`` for records created before the field
  existed.
"""


def migrate(cr, version):
    # `version` is None on a fresh install; there is nothing to migrate then.
    if not version:
        return

    cr.execute(
        """
        UPDATE disbursement_request
        SET partner_type = 'multi'
        WHERE partner_type IS DISTINCT FROM 'multi'
        """
    )

    cr.execute(
        """
        UPDATE disbursement_request_line l
        SET partner_id = r.partner_id
        FROM disbursement_request r
        WHERE l.request_id = r.id
          AND l.partner_id IS NULL
          AND r.partner_id IS NOT NULL
        """
    )

    cr.execute(
        """
        UPDATE disbursement_request
        SET payment_type = 'direct'
        WHERE payment_type IS NULL
        """
    )

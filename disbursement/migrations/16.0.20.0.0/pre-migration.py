# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration for 16.0.20.0.0 (ADR 0009).

``payment_type`` and ``partner_type_id`` move from the request to its lines, and
lines gain ``display_type`` (sections and notes). Each line takes its request's
values; the header columns are dropped by the ORM at the end of the update.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        ALTER TABLE disbursement_request_line
            ADD COLUMN IF NOT EXISTS payment_type varchar,
            ADD COLUMN IF NOT EXISTS partner_type_id integer,
            ADD COLUMN IF NOT EXISTS display_type varchar
        """
    )
    cr.execute(
        """
        UPDATE disbursement_request_line l
        SET payment_type = COALESCE(r.payment_type, 'direct'),
            partner_type_id = r.partner_type_id
        FROM disbursement_request r
        WHERE r.id = l.request_id
        """
    )
    # Until the ORM drops it, the old required column must not block inserts.
    cr.execute(
        "ALTER TABLE disbursement_request ALTER COLUMN partner_type_id DROP NOT NULL"
    )

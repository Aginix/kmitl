# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration for 16.0.8.0.0 (disbursement ADR-0009).

The payment subject (เรื่องที่จ่าย) moves onto each payment line: every line takes
its request's subject, still following it (not chosen by hand).
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        ALTER TABLE disbursement_payment_line
            ADD COLUMN IF NOT EXISTS payment_subject_id integer,
            ADD COLUMN IF NOT EXISTS payment_subject_manual boolean
        """
    )
    cr.execute(
        """
        UPDATE disbursement_payment_line pl
        SET payment_subject_id = r.payment_subject_id,
            payment_subject_manual = false
        FROM disbursement_request r
        WHERE r.id = pl.request_id
        """
    )

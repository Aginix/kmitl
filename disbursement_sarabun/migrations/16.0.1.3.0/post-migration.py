# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration for 16.0.1.3.0.

เลขที่หนังสือ (``memo_number``) is new and stamped from now on when e-Saraban
issues the number: requests whose หนังสือ was numbered before take it from
their latest numbered, not voided (ยกเลิกการส่ง) หนังสือ.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE disbursement_request dr
        SET memo_number = doc.name
        FROM (
            SELECT DISTINCT ON (origin_res_id) origin_res_id, name
            FROM sarabun_document
            WHERE origin_model = 'disbursement.request'
              AND register_number_id IS NOT NULL
              AND state != 'cancelled'
            ORDER BY origin_res_id, id DESC
        ) doc
        WHERE dr.id = doc.origin_res_id
          AND (dr.memo_number IS NULL OR dr.memo_number = '')
        """
    )

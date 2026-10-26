# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration for 16.0.13.0.0.

- ``note`` turns from Text into Html. The column stays ``text``; existing
  plain-text notes are wrapped as HTML so their line breaks survive in the
  editor and on the printed ใบขอเบิก.
- ``note`` is relabelled Note → Description (รายละเอียด): drop its stale Thai
  label so the module's th.po fills it in (an update keeps existing
  translations).
- ``sign_date`` (วันที่หน่วยงานลงนาม) is new: requests already past the head's
  signature take the day of their last tracked move to ``signed`` (the label
  is tracked, in Thai or English depending on who acted).
"""

from odoo.tools import plaintext2html


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT id, note FROM disbursement_request
        WHERE note IS NOT NULL AND note != '' AND note NOT LIKE '<%%'
        """
    )
    for rec_id, note in cr.fetchall():
        cr.execute(
            "UPDATE disbursement_request SET note = %s WHERE id = %s",
            (plaintext2html(note), rec_id),
        )
    cr.execute(
        """
        UPDATE ir_model_fields
        SET field_description = field_description - 'th_TH'
        WHERE model = 'disbursement.request' AND name = 'note'
        """
    )
    cr.execute(
        """
        UPDATE disbursement_request dr
        SET sign_date = signed.day
        FROM (
            SELECT m.res_id,
                   MAX(m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Bangkok')::date
                       AS day
            FROM mail_tracking_value t
            JOIN mail_message m ON m.id = t.mail_message_id
            JOIN ir_model_fields f ON f.id = t.field
            WHERE m.model = 'disbursement.request'
              AND f.name = 'state'
              AND t.new_value_char IN ('ลงนามแล้ว', 'Signed')
            GROUP BY m.res_id
        ) signed
        WHERE dr.id = signed.res_id
          AND dr.sign_date IS NULL
          AND dr.state NOT IN ('draft', 'submitted', 'cancel')
        """
    )

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration: ``note`` turns from Text into Html.

The column stays ``text``; existing plain-text notes are wrapped as HTML so
their line breaks survive in the editor and on the printed ใบขอเบิก.
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

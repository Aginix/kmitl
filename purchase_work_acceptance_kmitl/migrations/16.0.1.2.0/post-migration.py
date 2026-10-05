"""Backfill work_acceptance_attachment_rel from the previous compute-based
attachment_ids. Before this version, attachment_ids was derived at read time
from `search(res_model='work.acceptance', res_id=wa.id, res_field=False)
minus supporting_document_ids`. Now it is a plain stored M2M, so existing
attachments need to be inserted into the new relation to stay visible.
"""


def migrate(cr, version):
    cr.execute(
        """
        INSERT INTO work_acceptance_attachment_rel (wa_id, attachment_id)
        SELECT wa.id, att.id
        FROM work_acceptance wa
        JOIN ir_attachment att
          ON att.res_model = 'work.acceptance'
         AND att.res_id = wa.id
         AND (att.res_field IS NULL OR att.res_field = '')
        WHERE NOT EXISTS (
            SELECT 1 FROM work_acceptance_supporting_doc_rel sup
            WHERE sup.wa_id = wa.id AND sup.attachment_id = att.id
        )
        ON CONFLICT DO NOTHING
        """
    )

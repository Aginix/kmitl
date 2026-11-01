def migrate(cr, version):
    """Adopt enclosures uploaded before their หนังสือ was first saved (res_id=0),
    which recipients could not open."""
    cr.execute(
        """
        UPDATE ir_attachment a
           SET res_model = 'sarabun.document', res_id = r.document_id
          FROM sarabun_document_enclosure_rel r
         WHERE r.attachment_id = a.id
           AND (a.res_id IS NULL OR a.res_id = 0)
        """
    )

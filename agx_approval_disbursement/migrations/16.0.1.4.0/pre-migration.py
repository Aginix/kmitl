# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

MOVED_FIELD_XMLIDS = (
    "field_approval_request__disbursement_attachment_ids",
    "field_ir_attachment__is_disbursement_evidence",
)


def migrate(cr, version):
    """Hand the two attachment fields' xmlids over to ``agx_approval``, which
    now defines them.

    Upgrading ``agx_approval`` first re-reflects both fields and mints its own
    xmlid for each, so ``_process_end`` finds a second xid on the record and
    drops only the stale row. Upgrading *this* module alone never gives it that
    chance: the ``agx_approval_disbursement`` xid would be the only one left,
    ``_process_end`` would unlink the ``ir.model.fields`` record, and with it the
    ``approval_request_disbursement_attachment_rel`` table and every file link in
    it. Re-pointing the rows up front makes either upgrade order safe.
    """
    cr.execute(
        """
        UPDATE ir_model_data AS d
        SET module = 'agx_approval'
        WHERE d.module = 'agx_approval_disbursement'
          AND d.model = 'ir.model.fields'
          AND d.name IN %s
          AND NOT EXISTS (
              SELECT 1 FROM ir_model_data AS other
              WHERE other.module = 'agx_approval'
                AND other.name = d.name
          )
        """,
        (MOVED_FIELD_XMLIDS,),
    )

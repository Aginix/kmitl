# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    """Approval requests no longer take a returned DR for correction in place
    (ADR-0002). Requests left in the old post-bill ``returned`` state go back to
    ``billed``; their DRs stay at ``signed`` with the returned-to-source flag
    cleared, so the officer can return them again through the base flow (to
    their finance author). The pending correction To-Dos are dropped."""
    cr.execute(
        """
        SELECT dr.id, dr.approval_request_id
        FROM disbursement_request dr
        JOIN approval_request ar ON ar.id = dr.approval_request_id
        WHERE dr.returned_to_source IS TRUE
          AND dr.state != 'cancel'
          AND ar.state = 'returned'
        """
    )
    rows = cr.fetchall()
    if not rows:
        return
    dr_ids = tuple({r[0] for r in rows})
    ar_ids = tuple({r[1] for r in rows})
    cr.execute(
        """
        UPDATE disbursement_request
        SET returned_to_source = FALSE, return_source_reason = NULL
        WHERE id IN %s
        """,
        (dr_ids,),
    )
    cr.execute(
        "UPDATE approval_request SET state = 'billed' WHERE id IN %s",
        (ar_ids,),
    )
    cr.execute(
        """
        DELETE FROM mail_activity ma
        USING ir_model_data imd
        WHERE imd.model = 'mail.activity.type'
          AND imd.module = 'disbursement'
          AND imd.name IN (
              'mail_activity_source_correct', 'mail_activity_dr_await'
          )
          AND ma.activity_type_id = imd.res_id
          AND (
              (ma.res_model = 'approval.request' AND ma.res_id IN %s)
              OR (ma.res_model = 'disbursement.request' AND ma.res_id IN %s)
          )
        """,
        (ar_ids, dr_ids),
    )

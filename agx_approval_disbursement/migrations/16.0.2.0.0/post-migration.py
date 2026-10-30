# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    """Approval requests no longer take a returned DR for correction in place
    (ADR-0002), and are disbursed per Expense (agx_approval ADR-0010).

    - Requests left in the old post-bill ``returned`` state go back to
      ``approved`` (open for disbursement); their DRs stay where they are with
      the returned-to-source flag cleared, so the officer can return them again
      through the base flow (to their finance author). The pending correction
      To-Dos are dropped.
    - Every existing ใบขอเบิก states its whole total as its request's first
      Expense (ค่าใช้จ่ายที่ขอเบิก) — the old requests almost all have a single
      one."""
    cr.execute(
        """
        INSERT INTO disbursement_request_approval_expense
            (request_id, approval_request_line_id, amount, sequence,
             create_uid, write_uid, create_date, write_date)
        SELECT dr.id, first.id, dr.amount_total, 10,
               1, 1, now() at time zone 'UTC', now() at time zone 'UTC'
        FROM disbursement_request dr,
             LATERAL (
                 SELECT l.id FROM approval_request_line l
                 WHERE l.request_id = dr.approval_request_id
                 ORDER BY l.sequence, l.id LIMIT 1
             ) first
        WHERE dr.approval_request_id IS NOT NULL
          AND dr.amount_total > 0
          AND NOT EXISTS (
              SELECT 1 FROM disbursement_request_approval_expense e
              WHERE e.request_id = dr.id
          )
        """
    )
    # "Correction submitted" To-Dos on requests corrected before the upgrade
    # were resolved through the DR's return source, which approval requests no
    # longer are — nothing would ever close them.
    cr.execute(
        """
        DELETE FROM mail_activity ma
        USING ir_model_data imd
        WHERE imd.model = 'mail.activity.type'
          AND imd.module = 'disbursement'
          AND imd.name = 'mail_activity_source_done'
          AND ma.activity_type_id = imd.res_id
          AND ma.res_model = 'approval.request'
        """
    )
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
        "UPDATE approval_request SET state = 'approved' WHERE id IN %s",
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

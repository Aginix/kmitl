# Labels renamed to Thai source strings (testing feedback, 2026-10): `-u`
# rewrites en_US but keeps the old th_TH translation, so Thai users would go
# on seeing the old label. Drop the stale key so the new source string shows.
RENAMED_FIELDS = (
    "name",
    "contract_number",
    "effective_date",
    "return_due_date",
    "actual_expense_amount",
    "amount_remaining",
    "date_submitted",
    "date_endorsed",
    "date_verified",
    "date_approved",
    "date_closed",
)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_fields
           SET field_description = field_description - 'th_TH'
         WHERE model = 'advance.payment'
           AND name IN %s
        """,
        (RENAMED_FIELDS,),
    )
    # Every state label is a Thai source string now; the old th.po mapped
    # them from English (Draft → ฉบับร่าง, In Progress → กำลังดำเนินการ, …).
    cr.execute(
        """
        UPDATE ir_model_fields_selection s
           SET name = s.name - 'th_TH'
          FROM ir_model_fields f
         WHERE s.field_id = f.id
           AND f.model = 'advance.payment'
           AND f.name = 'state'
        """
    )
    _retype_step_todos(cr)


# Open step To-Dos raised under the generic "To Do" type before each step got
# its own type: re-point them by their summary prefix, and drop the ones of
# the steps removed with the expense report (ADR-0028).
STEP_TODOS = {
    "เห็นชอบคำขอยืมเงิน": "mail_activity_type_endorse",
    "ตรวจสอบคำขอยืมเงิน": "mail_activity_type_verify",
    "พิจารณาคำขอยืมเงิน": "mail_activity_type_director_review",
    "อนุมัติคำขอยืมเงิน": "mail_activity_type_approve",
    "สร้างใบสำคัญจ่ายเงินยืม": "mail_activity_type_payment_voucher",
}
REMOVED_STEP_TODOS = ("ส่งรายงานค่าใช้จ่ายเงินยืม", "ตรวจรับรายงานค่าใช้จ่ายเงินยืม", "คืนเงินยืม")


def _retype_step_todos(cr):
    cr.execute(
        "SELECT res_id FROM ir_model_data"
        " WHERE module = 'mail' AND name = 'mail_activity_data_todo'"
    )
    row = cr.fetchone()
    if not row:
        return
    generic = row[0]
    for prefix, xmlid in STEP_TODOS.items():
        cr.execute(
            """
            UPDATE mail_activity a
               SET activity_type_id = d.res_id
              FROM ir_model_data d
             WHERE d.module = 'advance_payment' AND d.name = %s
               AND a.res_model = 'advance.payment'
               AND a.activity_type_id = %s
               AND a.summary LIKE %s
            """,
            (xmlid, generic, prefix + " %"),
        )
    for prefix in REMOVED_STEP_TODOS:
        cr.execute(
            """
            DELETE FROM mail_activity
             WHERE res_model = 'advance.payment'
               AND activity_type_id = %s
               AND summary LIKE %s
            """,
            (generic, prefix + " %"),
        )

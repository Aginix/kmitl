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
    cr.execute(
        """
        UPDATE ir_model_fields
           SET field_description = field_description - 'th_TH'
         WHERE model = 'advance.payment.return.wizard'
           AND name IN ('actual_expense_amount', 'amount_remaining')
        """
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

def migrate(cr, version):
    """The digest templates are noupdate and printed `return_amount`, which
    left with the in-app returns (advance_payment ADR-0028): show คงเหลือ."""
    cr.execute(
        """
        UPDATE mail_template t
           SET body_html = replace(
                   replace(t.body_html::text, 'loan.return_amount', 'loan.amount_remaining'),
                   'ยอดที่ต้องคืน', 'คงเหลือ'
               )::jsonb
          FROM ir_model_data d
         WHERE d.model = 'mail.template'
           AND d.res_id = t.id
           AND d.module = 'advance_payment_followup'
        """
    )
    # The followup reminder now has its own activity type.
    cr.execute(
        """
        UPDATE mail_activity a
           SET activity_type_id = d.res_id
          FROM ir_model_data d, ir_model_data g
         WHERE d.module = 'advance_payment_followup'
           AND d.name = 'mail_activity_type_followup'
           AND g.module = 'mail' AND g.name = 'mail_activity_data_todo'
           AND a.res_model = 'advance.payment'
           AND a.activity_type_id = g.res_id
           AND a.summary LIKE 'ติดตามลูกหนี้เงินยืม %%'
        """
    )

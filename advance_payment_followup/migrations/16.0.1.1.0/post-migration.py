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

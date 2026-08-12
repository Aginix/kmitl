def migrate(cr, version):
    """Give the payment vouchers that already exist a finance status.

    The field is new, so every row would default to ``draft`` — saying that the
    finance office has not started on vouchers they finished months ago, unfreezing
    the money side of every one of them, and refusing to post any that are still
    waiting for an approver. Derived from what the old shape recorded instead:

    * posted, or the bank result was success → **paid** (the money left and the
      finance office said so);
    * already in an e-payment file, or locked for the accounting office
      (``submitted``) → **confirmed**;
    * anything else → **draft**.

    In-flight vouchers keep their own ``state``: one already waiting in the approval
    queue finishes the way it started (Approve = post), and nothing is walked
    backwards to hand an accounting maker a step they were not expecting. Only
    vouchers made from here on run the new shape.
    """
    cr.execute(
        """
        UPDATE account_payment ap
           SET finance_state = CASE
                WHEN am.state = 'posted' OR ap.bank_result_status = 'success'
                    THEN 'paid'
                WHEN ap.export_status IN ('to_export', 'exported')
                     OR am.state = 'submitted'
                    THEN 'confirmed'
                ELSE 'draft'
               END
          FROM account_move am
         WHERE am.id = ap.move_id
        """
    )

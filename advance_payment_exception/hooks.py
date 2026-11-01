RULES = (
    "excep_loan_amount_too_low",
    "excep_loan_amount_too_high",
    "excep_missing_bank_account",
    "excep_missing_reference",
    "excep_missing_manager",
)


def pre_init_hook(cr):
    """Adopt the rules advance_payment used to ship (ADR-0024).

    They are noupdate, so `-u advance_payment` keeps them; installed in the
    same run, this module would add a second copy of each, and the old
    domain-based excep_missing_bank_account would still block the unlisted
    bank account. Re-pointing their xmlids lets this module's data update
    them in place instead.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'advance_payment_exception'
         WHERE module = 'advance_payment'
           AND model = 'exception.rule'
           AND name IN %s
        """,
        (RULES,),
    )

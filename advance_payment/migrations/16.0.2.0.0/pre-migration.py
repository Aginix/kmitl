def migrate(cr, version):
    """Drop the exception rules whose fields left this module.

    `excep_missing_department` filtered on `department_id` and
    `excep_missing_analytic` read the four `*_analytic_id` dimensions; both
    fields are gone from `advance.payment` (the dimensions moved to
    advance_payment_budget together with a fresh copy of the rule).

    Odoo's own orphan-external-id cleanup normally removes them, but it is
    skipped for records that were already detached from their module, and a
    leftover rule is not harmless: base_exception evaluates every active rule
    on the model, so a single stale one makes *every* `action_submit` fail with
    an AttributeError raised from inside `_rule_eval`.
    """
    obsolete = ("excep_missing_department", "excep_missing_analytic")
    cr.execute(
        """
        DELETE FROM exception_rule
         WHERE id IN (
               SELECT res_id
                 FROM ir_model_data
                WHERE module = 'advance_payment'
                  AND model = 'exception.rule'
                  AND name IN %s
               )
        """,
        (obsolete,),
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'advance_payment'
           AND model = 'exception.rule'
           AND name IN %s
        """,
        (obsolete,),
    )

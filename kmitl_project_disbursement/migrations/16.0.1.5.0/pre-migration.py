"""Pre-migration for 16.0.1.5.0.

The "budget code has no account" exception rule is retired: core refuses a line
without an account on submit for every request. Archive the rule (and make its
XML id noupdate) instead of letting the update delete it, so requests that
logged it keep their history.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data SET noupdate = TRUE
        WHERE module = 'kmitl_project_disbursement' AND name = 'excep_disbursement_project_no_product'
        """
    )
    cr.execute(
        """
        UPDATE exception_rule SET active = FALSE
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'kmitl_project_disbursement' AND name = 'excep_disbursement_project_no_product'
        )
        """
    )

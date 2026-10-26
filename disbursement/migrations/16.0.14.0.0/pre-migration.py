# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: the standalone ใบขอเบิก print moves to ``disbursement_pdf``.

Re-point the report's xmlids to the new module before ``disbursement`` loads,
so the update does not delete them as obsolete records: the paperformat, the
report action and its templates keep their ids (and the view inheritors in
``disbursement_budget`` / ``kmitl_project_disbursement`` stay attached) until
``disbursement_pdf`` is installed and takes them over (ADR 0006). A second run
finds no ``disbursement`` rows left and does nothing.
"""

XMLIDS = (
    "paperformat_disbursement_request_report",
    "action_report_disbursement_request",
    "report_disbursement_request",
    "report_disbursement_request_signature",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = 'disbursement_pdf'
        WHERE module = 'disbursement' AND name IN %s
        """,
        (XMLIDS,),
    )

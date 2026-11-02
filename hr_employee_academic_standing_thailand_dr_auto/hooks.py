import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Back-fill ``title_dr`` for existing employees.

    ``title_dr`` already exists as a plain stored column created by the base
    module, so simply adding the compute here does not make Odoo recompute it
    for existing records. Flag the source field as modified to recompute
    ``title_dr`` and, in turn, ``academic_standing_title``.
    """
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    employees = env["hr.employee"].with_context(active_test=False).search([])
    employees.modified(["education_level_id"])
    env.flush_all()
    _logger.info(
        "hr_employee_academic_standing_thailand_dr_auto: "
        "recomputed title_dr for %s employees",
        len(employees),
    )

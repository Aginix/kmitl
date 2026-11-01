import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Backfill existing employees: rebuild name (Thai) and name_secondary
    (English) so they carry the work-track title prefix right after install."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    employees = env["hr.employee"].with_context(active_test=False).search([])
    employees._compute_name_secondary()
    employees._sync_name_title()
    _logger.info("hr_employee_name_title_kmitl: synced %s employees", len(employees))

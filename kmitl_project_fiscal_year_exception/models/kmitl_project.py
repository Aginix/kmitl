from odoo import fields, models
from odoo.tools import config


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _exception_fiscal_year_not_current(self):
        """True when the ปีงบประมาณ picked on submit is not the current one (the
        year whose date range covers today). Silent once past the submit states so
        documents already in progress are never blocked at later gates."""
        self.ensure_one()
        # Existing suites hard-code a past ปีงบ; only this module's own tests
        # opt in via the context key.
        if config["test_enable"] and not self.env.context.get(
            "test_fiscal_year_exception"
        ):
            return False
        if self.state not in ("draft", "returned"):
            return False
        fy = self.account_fiscal_year_id
        today = fields.Date.context_today(self)
        return not fy or not (fy.date_from <= today <= fy.date_to)

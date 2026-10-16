from datetime import date, timedelta

from odoo.tests.common import TransactionCase, tagged

CTX = {"test_fiscal_year_exception": True}


def _current_fy(env):
    today = date.today()
    return env["account.fiscal.year"].search(
        [("date_from", "<=", today), ("date_to", ">=", today)], limit=1
    ) or env["account.fiscal.year"].create(
        {
            "name": "FY-CURRENT-EXC",
            "date_from": today - timedelta(days=100),
            "date_to": today + timedelta(days=100),
            "company_id": env.company.id,
        }
    )


def _past_fy(env):
    return env["account.fiscal.year"].create(
        {
            "name": "FY-PAST-EXC",
            "date_from": date(2001, 10, 1),
            "date_to": date(2002, 9, 30),
            "company_id": env.company.id,
        }
    )


@tagged("post_install", "-at_install")
class TestApprovalRequestFiscalYearException(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.current_fy = _current_fy(cls.env)
        cls.past_fy = _past_fy(cls.env)
        cls.Model = cls.env["approval.request"].with_context(**CTX)

    def _new(self, state, fy):
        return self.Model.new({"state": state, "account_fiscal_year_id": fy.id})

    def test_past_year_fails_current_passes(self):
        self.assertTrue(
            self._new("draft", self.past_fy)._exception_fiscal_year_not_current()
        )
        self.assertFalse(
            self._new("draft", self.current_fy)._exception_fiscal_year_not_current()
        )

    def test_silent_past_submit(self):
        self.assertFalse(
            self._new("to_verify", self.past_fy)._exception_fiscal_year_not_current()
        )

    def test_test_mode_bypass_without_context(self):
        rec = self.env["approval.request"].new(
            {"state": "draft", "account_fiscal_year_id": self.past_fy.id}
        )
        self.assertFalse(rec._exception_fiscal_year_not_current())

    def test_old_rule_archived(self):
        rule = self.env.ref("agx_approval.excep_submit_date_outside_fy")
        self.assertFalse(rule.active)

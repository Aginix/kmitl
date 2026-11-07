from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvanceLegacy(TransactionCase):
    """เงินยืม (ระบบเก่า): the borrower is the only payee and nothing is paid out."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env["disbursement.request"]
        cls.employee = cls.env["hr.employee"].create({"name": "Legacy Borrower"})
        cls.partner = cls.employee.work_contact_id
        cls.partner.partner_type_id = cls.env["res.partner.type"].search(
            [("is_internal", "=", True)], limit=1
        )
        cls.other = cls.env["res.partner"].create({"name": "Someone Else"})
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        # One account per required dimension: submit checks they are complete.
        Analytic = cls.env["account.analytic.account"]
        cls.distribution = {
            str(Analytic.search([("root_plan_id.code", "=", code)], limit=1).id): 100
            for code in cls.DR._analytic_keys
        }

    def _request(self, partner=None, **vals):
        return self.DR.create(
            {
                "payment_type": "advance_legacy",
                "legacy_advance_employee_id": self.employee.id,
                "legacy_advance_contract_number": "OLD-001",
                "partner_type_id": self.partner.partner_type_id.id,
                "analytic_distribution": self.distribution,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.expense_account.id,
                            "name": "line",
                            "amount": 100.0,
                            "partner_id": (partner or self.partner).id,
                        },
                    )
                ],
                **vals,
            }
        )

    def test_borrower_fills_the_payee(self):
        # Not saved: only the onchanges are under test.
        form = Form(self.DR)
        form.payment_type = "advance_legacy"
        form.legacy_advance_employee_id = self.employee
        self.assertEqual(form.line_ids.edit(0).partner_id, self.partner)
        self.assertFalse(form.has_tax)

    def test_pays_nothing_out(self):
        self.assertFalse(self._request().pays_out)

    def test_payee_must_be_the_borrower(self):
        with self.assertRaises(ValidationError):
            self._request(partner=self.other)

    def test_fields_only_on_legacy_type(self):
        with self.assertRaises(ValidationError):
            self._request(payment_type="direct")

    def test_submit_requires_contract_number(self):
        request = self._request()
        request.legacy_advance_contract_number = False
        with self.assertRaises(UserError):
            request.action_submit()

    def test_submit_requires_borrower(self):
        request = self._request()
        request.legacy_advance_employee_id = False
        with self.assertRaises(UserError):
            request.action_submit()

    def test_submit_not_blocked_by_in_system_loan_guard(self):
        """advance_payment_disbursement's loan requirement keys on ``advance``."""
        request = self._request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")

    def test_external_payee_type_blocked_at_submit(self):
        external = self.env["res.partner.type"].search(
            [("is_internal", "=", False)], limit=1
        )
        request = self._request(partner_type_id=external.id)
        rule = self.env.ref(
            "disbursement_advance_legacy.excep_disbursement_advance_legacy_internal_payee"
        )
        self.assertIn(rule.id, request.detect_exceptions())
        request.action_submit()
        self.assertEqual(request.state, "draft")

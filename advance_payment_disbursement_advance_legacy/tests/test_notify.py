from odoo.tests.common import TransactionCase, tagged

from ..models.disbursement_request import ACTIVITY


@tagged("post_install", "-at_install")
class TestNotify(TransactionCase):
    """The loan officer in Settings is told when a legacy advance request
    consumes the budget, and the notice is withdrawn when it is undone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Loan Officer",
                "login": "apdal_officer",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("advance_payment.group_advance_payment_loan_officer").id),
                ],
            }
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.default_loan_verifier_id", cls.officer.id
        )
        employee = cls.env["hr.employee"].create({"name": "Legacy Borrower"})
        partner = employee.work_contact_id
        partner.partner_type_id = cls.env["res.partner.type"].search(
            [("is_internal", "=", True)], limit=1
        )
        account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.request = cls.env["disbursement.request"].create(
            {
                "payment_type": "advance_legacy",
                "legacy_advance_employee_id": employee.id,
                "legacy_advance_contract_number": "OLD-9",
                "partner_type_id": partner.partner_type_id.id,
                "line_ids": [
                    (0, 0, {"name": "x", "account_id": account.id, "amount": 300.0,
                            "partner_id": partner.id})
                ],
            }
        )

    def _notices(self):
        return self.request.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref(ACTIVITY)
        )

    def test_consume_notifies_and_reversal_withdraws(self):
        self.request.budget_consumed_amount = 300.0
        notice = self._notices()
        self.assertEqual(notice.user_id, self.officer)
        self.assertIn("OLD-9", notice.summary)
        self.request.budget_consumed_amount = 0.0
        self.assertFalse(self._notices())

    def test_other_payment_types_not_notified(self):
        self.request.write({"payment_type": "direct", "legacy_advance_employee_id": False,
                            "legacy_advance_contract_number": False})
        self.request.budget_consumed_amount = 300.0
        self.assertFalse(self._notices())

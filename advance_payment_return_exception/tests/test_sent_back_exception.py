from odoo.tests.common import TransactionCase, tagged


class SentBackCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env["res.users"]
        cls.officer = Users.create(
            {
                "name": "Loan Officer",
                "login": "officer_ap_sent_back",
                "groups_id": [
                    (
                        6,
                        0,
                        cls.env.ref(
                            "advance_payment.group_advance_payment_loan_officer"
                        ).ids,
                    )
                ],
            }
        )
        cls.supervisor = Users.create(
            {
                "name": "Supervisor",
                "login": "supervisor_ap_sent_back",
                "groups_id": [
                    (
                        6,
                        0,
                        cls.env.ref(
                            "advance_payment.group_advance_payment_own_only"
                        ).ids,
                    )
                ],
            }
        )
        Employee = cls.env["hr.employee"]
        cls.emp = Employee.search(
            [("user_id", "=", cls.env.ref("base.user_admin").id)], limit=1
        )
        cls.emp.parent_id = Employee.create(
            {"name": "Supervisor", "user_id": cls.supervisor.id}
        )
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )
        cls.bank = cls.env["res.partner.bank"].create(
            {"acc_number": "sent-back-1", "partner_id": cls.emp.work_contact_id.id}
        )
        cls.marker = cls.env.ref(
            "advance_payment_return_exception.excep_advance_payment_sent_back"
        )

    def _submitted(self):
        loan = self.env["advance.payment"].create(
            {
                "employee_id": self.emp.id,
                "loan_amount": 1000,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "bank_id": self.bank.id,
                "loan_verifier_id": self.officer.id,
            }
        )
        loan.action_submit()
        self.assertEqual(loan.state, "to_endorse")
        return loan


@tagged("post_install", "-at_install")
class TestSentBackException(SentBackCommon):
    def test_supervisor_send_back_marks_until_resubmitted(self):
        loan = self._submitted()
        loan.with_user(self.supervisor).action_endorse_reject()
        self.assertEqual(loan.state, "draft")
        self.assertEqual(loan.main_exception_id, self.marker)
        # Detection leaves the marker alone and does not pop it up.
        self.assertFalse(loan.detect_exceptions())
        self.assertIn(self.marker, loan.exception_ids)
        loan.action_submit()
        self.assertEqual(loan.state, "to_endorse")
        self.assertNotIn(self.marker, loan.exception_ids)

    def test_officer_send_back_marks(self):
        loan = self._submitted()
        loan.action_endorse()
        loan.with_user(self.officer).action_reset_to_draft()
        self.assertIn(self.marker, loan.exception_ids)

    def test_send_back_clears_an_earlier_ignore(self):
        loan = self._submitted()
        loan.ignore_exception = True
        loan.with_user(self.supervisor).action_endorse_reject()
        self.assertFalse(loan.ignore_exception)
        self.assertEqual(loan.main_exception_id, self.marker)

    def test_pull_back_does_not_mark(self):
        loan = self._submitted()
        loan.with_user(self.env.ref("base.user_admin")).action_recall()
        self.assertEqual(loan.state, "draft")
        self.assertNotIn(self.marker, loan.exception_ids)

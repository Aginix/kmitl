from odoo.tests.common import TransactionCase, tagged

# 1x1 transparent PNG
SIGNATURE = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8"
    b"AAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestOfficeRoute(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.office_ou = cls.env["operating.unit"].create(
            {
                "name": "Test Office",
                "code": "TOFF",
                "partner_id": cls.env.company.partner_id.id,
            }
        )
        cls.faculty_ou = cls.env["operating.unit"].create(
            {
                "name": "Test Faculty",
                "code": "TFAC",
                "partner_id": cls.env.company.partner_id.id,
            }
        )
        cls.env.company.advance_payment_office_ou_ids = cls.office_ou
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )
        cls.employee = cls.env.ref("hr.employee_admin")
        # A named endorser, so advance_payment_exception (when installed)
        # does not block the Standard-route submit for a missing supervisor.
        cls.supervisor = cls.env["res.users"].create(
            {"name": "Office Route Supervisor", "login": "office_route_supervisor"}
        )
        cls.bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "OFFICE-ROUTE-001",
                "partner_id": cls.employee.work_contact_id.id,
            }
        )

    def _make(self, ou):
        return self.env["advance.payment"].create(
            {
                "employee_id": self.employee.id,
                "loan_amount": 300,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "loan_verifier_id": self.env.ref("base.user_admin").id,
                "operating_unit_id": ou.id,
                "bank_id": self.bank.id,
                "endorser_id": self.supervisor.id,
            }
        )

    def test_office_ou_skips_endorsement(self):
        ap = self._make(self.office_ou)
        self.assertTrue(ap.is_office_route)
        self.assertEqual(
            ap._get_route_states(), ["to_verify", "to_director", "to_approve"]
        )
        ap.action_submit()
        self.assertEqual(ap.state, "to_verify")
        self.assertFalse(ap.endorser_id)
        self.assertFalse(ap._workflow_activities("to_endorse"))
        ap.action_verify()
        self.assertEqual(ap.state, "to_director")
        ap.action_director_review()
        self.assertEqual(ap.state, "to_approve")
        ap.action_approve()
        self.assertEqual(ap.state, "approved")

    def test_faculty_ou_keeps_standard_route(self):
        ap = self._make(self.faculty_ou)
        self.assertFalse(ap.is_office_route)
        ap.action_submit()
        self.assertEqual(ap.state, "to_endorse")

    def test_route_fixed_at_submit(self):
        """A Settings change after submit must not re-route the request."""
        ap = self._make(self.office_ou)
        ap.action_submit()
        self.env.company.advance_payment_office_ou_ids = False
        self.assertTrue(ap.is_office_route)
        self.assertNotIn("to_endorse", ap._get_route_states())

    def test_settings_change_before_submit_is_picked_up(self):
        ap = self._make(self.faculty_ou)
        self.env.company.advance_payment_office_ou_ids = self.faculty_ou
        ap.action_submit()
        self.assertTrue(ap.is_office_route)
        self.assertEqual(ap.state, "to_verify")

    def test_director_signs_the_endorser_block(self):
        ap = self._make(self.office_ou)
        ap.director_id.employee_id.signature = SIGNATURE
        ap.action_submit()
        ap.action_verify()
        self.assertFalse(ap._contract_signatures()["endorser"]["signature"])
        ap.action_director_review()
        sig = ap._contract_signatures()["endorser"]
        self.assertEqual(sig["employee"], ap.director_id.employee_id)
        self.assertEqual(sig["signature"], SIGNATURE)
        self.assertTrue(sig["date"])
        # The director's own title, not the fixed "ผู้บังคับบัญชา".
        self.assertNotIn("position", sig)

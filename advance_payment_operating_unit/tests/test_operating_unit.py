from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvancePaymentOperatingUnit(TransactionCase):
    """A loan belongs to the borrower's unit, not the drafter's (ADR-0031)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        OU = cls.env["operating.unit"]
        partner = cls.env.company.partner_id
        cls.faculty = OU.create(
            {"name": "Faculty", "code": "TF1", "partner_id": partner.id}
        )
        cls.office = OU.create(
            {"name": "Office", "code": "TO1", "partner_id": partner.id}
        )
        groups = cls.env.ref("advance_payment.group_advance_payment_loan_officer")
        cls.officer = cls.env["res.users"].create(
            {
                "name": "Officer",
                "login": "officer_ap_ou",
                "groups_id": [(6, 0, groups.ids)],
                "operating_unit_ids": [(6, 0, (cls.office | cls.faculty).ids)],
                "default_operating_unit_id": cls.office.id,
            }
        )
        borrower = cls.env["res.users"].create(
            {
                "name": "Borrower",
                "login": "borrower_ap_ou",
                "operating_unit_ids": [(6, 0, cls.faculty.ids)],
                "default_operating_unit_id": cls.faculty.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Borrower", "user_id": borrower.id}
        )

    def test_officer_drafts_in_borrowers_unit(self):
        loan = (
            self.env["advance.payment"]
            .with_user(self.officer)
            .create(
                {
                    "employee_id": self.employee.id,
                    "loan_amount": 100,
                    "loan_type_id": self.env.ref("advance_payment.loan_type_other").id,
                    "loan_reason": "Test reason",
                    "loan_verifier_id": self.officer.id,
                }
            )
        )
        self.assertEqual(loan.operating_unit_id, self.faculty)

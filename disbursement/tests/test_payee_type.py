# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.tests.common import tagged

from .test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestPayeeType(TwoApproverCommon):
    """Payees live on the lines, all of the header's payee type, each with a
    bank account; the fiscal year is chosen on the request."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.student_type = cls.env.ref("partner_type_kmitl.partner_type_student")
        cls.student = cls.env["res.partner"].create({
            "name": "Student",
            "partner_type_id": cls.student_type.id,
            "bank_ids": [(0, 0, {"acc_number": "9876543210"})],
        })

    def _draft(self, partner, **vals):
        dr = self.DR.create({
            "partner_type_id": self.partner.partner_type_id.id,
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "name": "line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "partner_id": partner.id,
            })],
            **vals,
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        return dr

    def test_payee_of_another_type_blocks_submit(self):
        dr = self._draft(self.student)
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref("disbursement.excep_disbursement_line_partner_type"),
            dr.exception_ids,
        )

    def test_payee_without_bank_blocks_submit_until_added(self):
        self.partner.bank_ids.unlink()
        dr = self._draft(self.partner)
        self.assertFalse(dr.line_ids.partner_bank_id)
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref("disbursement.excep_disbursement_line_partner_bank"),
            dr.exception_ids,
        )
        # Adding the account on the partner fills the line in.
        bank = self.env["res.partner.bank"].create(
            {"partner_id": self.partner.id, "acc_number": "1112223334"}
        )
        self.assertEqual(dr.line_ids.partner_bank_id, bank)
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")

    def test_new_bank_keeps_chosen_account(self):
        dr = self._draft(self.partner)
        chosen = dr.line_ids.partner_bank_id
        self.env["res.partner.bank"].create(
            {"partner_id": self.partner.id, "acc_number": "5556667778"}
        )
        self.assertEqual(dr.line_ids.partner_bank_id, chosen)

    def test_changing_type_warns_about_mismatched_payees(self):
        dr = self._draft(self.partner)
        dr.partner_type_id = self.student_type
        result = dr._onchange_partner_type_id()
        self.assertIn(self.partner.display_name, result["warning"]["message"])
        # The warning does not clear the lines; submit still guards them.
        self.assertEqual(dr.line_ids.partner_id, self.partner)

    def test_payee_search_and_display(self):
        dr = self._draft(self.partner)
        self.assertEqual(dr.payee_display, self.partner.display_name)
        found = self.DR.search([("line_ids.partner_id", "ilike", "Vendor")])
        self.assertIn(dr, found)

    def test_number_follows_chosen_fiscal_year(self):
        fy = self.env["account.fiscal.year"].create({
            "name": "2599",
            "date_from": date(2056, 10, 1),
            "date_to": date(2057, 9, 30),
            "company_id": self.env.company.id,
        })
        dr = self._draft(self.partner, account_fiscal_year_id=fy.id)
        self.assertEqual(dr.account_fiscal_year_id, fy)
        self.assertTrue(dr.name.startswith("DR/99/"))
        self.assertIn(dr, self.DR.search([("account_fiscal_year_id", "=", fy.id)]))

    def test_missing_bank_can_be_ignored_for_cash(self):
        """Not blocking: a cash payee needs no account, so the rule may be
        ignored and the request submitted."""
        self.partner.bank_ids.unlink()
        dr = self._draft(self.partner)
        dr.action_submit()
        dr.action_ignore_exceptions()
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")

    def test_submitted_line_keeps_its_bank(self):
        dr = self._draft(self.partner)
        dr.action_submit()
        bank = dr.line_ids.partner_bank_id
        self.assertTrue(bank)
        bank.active = False
        self.assertEqual(dr.line_ids.partner_bank_id, bank)

    def test_moving_draft_to_another_year_renumbers_it(self):
        fy = self.env["account.fiscal.year"].create({
            "name": "2598",
            "date_from": date(2055, 10, 1),
            "date_to": date(2056, 9, 30),
            "company_id": self.env.company.id,
        })
        dr = self._draft(self.partner)
        dr.account_fiscal_year_id = fy
        self.assertTrue(dr.name.startswith("DR/98/"))

    def test_date_edit_keeps_the_chosen_year(self):
        fy = self.env["account.fiscal.year"].create({
            "name": "2597",
            "date_from": date(2054, 10, 1),
            "date_to": date(2055, 9, 30),
            "company_id": self.env.company.id,
        })
        dr = self._draft(self.partner, account_fiscal_year_id=fy.id)
        dr.date = date(2020, 1, 1)
        dr._onchange_date_fiscal_year()
        self.assertEqual(dr.account_fiscal_year_id, fy)

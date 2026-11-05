# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.tests.common import tagged

from .test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestPayeeType(TwoApproverCommon):
    """Payees live on the lines, each with its own payee type, payment type
    and bank account (ADR 0009); the fiscal year is chosen on the request."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.student_type = cls.env.ref("partner_type_kmitl.partner_type_student")
        cls.student = cls.env["res.partner"].create({
            "name": "Student",
            "partner_type_id": cls.student_type.id,
            "bank_ids": [(0, 0, {"acc_number": "9876543210"})],
        })

    def _line(self, partner, **vals):
        return (0, 0, {
            "account_id": self.expense_account.id,
            "name": "line",
            "amount": 100.0,
            "partner_id": partner.id,
            **vals,
        })

    def _draft(self, partner, line_vals=None, extra_lines=(), **vals):
        dr = self.DR.create({
            "line_ids": [self._line(partner, **(line_vals or {}))] + list(extra_lines),
            **vals,
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        return dr

    def test_line_type_follows_the_payee(self):
        dr = self._draft(self.student)
        self.assertEqual(dr.line_ids.partner_type_id, self.student_type)
        self.assertEqual(dr.payee_type_display, self.student_type.display_name)

    def test_payee_of_another_type_blocks_submit(self):
        dr = self._draft(self.student)
        dr.line_ids.partner_type_id = self.partner.partner_type_id
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref("disbursement.excep_disbursement_line_partner_type"),
            dr.exception_ids,
        )

    def test_prepaid_to_external_payee_blocks_submit(self):
        dr = self._draft(self.partner, line_vals={"payment_type": "prepaid"})
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref("disbursement.excep_disbursement_advance_internal_payee"),
            dr.exception_ids,
        )

    def test_prepaid_to_internal_staff_submits(self):
        staff_type = self.env.ref("partner_type_kmitl.partner_type_employee")
        staff = self.env["res.partner"].create({
            "name": "Staff",
            "partner_type_id": staff_type.id,
            "bank_ids": [(0, 0, {"acc_number": "4445556667"})],
        })
        dr = self._draft(staff, line_vals={"payment_type": "prepaid"})
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")

    def test_one_request_mixes_payees_and_payment_types(self):
        staff_type = self.env.ref("partner_type_kmitl.partner_type_employee")
        staff = self.env["res.partner"].create({
            "name": "Staff",
            "partner_type_id": staff_type.id,
            "bank_ids": [(0, 0, {"acc_number": "4445556668"})],
        })
        dr = self._draft(
            self.partner,
            extra_lines=[self._line(staff, payment_type="prepaid")],
        )
        self.assertEqual(
            set(dr.line_ids.mapped("payment_type")), {"direct", "prepaid"}
        )
        self.assertIn(",", dr.payment_type_display)
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")

    def test_section_row_is_never_paid(self):
        dr = self._draft(
            self.partner,
            extra_lines=[(0, 0, {"display_type": "line_section", "name": "Food"})],
        )
        section = dr.line_ids.filtered("display_type")
        self.assertFalse(section.account_id)
        self.assertFalse(section.payment_type)
        self.assertFalse(section.pays_out)
        self.assertEqual(dr._product_lines(), dr.line_ids - section)
        self.assertEqual(dr.amount_total, 100.0)
        self.assertTrue(dr._has_sections())
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")

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
        # Numbered on submit, not on create: a draft is still "/".
        self.assertEqual(dr.name, "/")
        dr.action_submit()
        self.assertTrue(dr.name.startswith("DR/99/"))
        # ...and keeps its number when reset to draft.
        number = dr.name
        dr.action_draft()
        self.assertEqual(dr.name, number)
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
        dr.action_submit()
        dr.action_draft()
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

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCashRevenueHandover(TransactionCase):
    """The handover entry raised when a centrally-funded disbursement is billed.

    The activity hierarchy is built to match the real chart — ``09`` (sector) →
    ``09007`` (program) → ``090070101`` (main) → ``09007010110`` (secondary) →
    ``09007010110170`` (sub) — because rolling the activity up to the level
    central holds it at is the one piece of the entry that is derived rather
    than configured.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Move = cls.env["account.move"]
        cls.Analytic = cls.env["account.analytic.account"]

        cls.plans = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = cls.env["account.analytic.plan"].search(
                [("code", "=", code)], limit=1
            )
            if not plan:
                plan = cls.env["account.analytic.plan"].create(
                    {"name": code.title(), "code": code}
                )
            cls.plans[code] = plan

        # Departments: central, one of its own sub-units, and a faculty.
        cls.dept_central = cls._analytic("departments", "T89", "Central Office")
        cls.dept_central_child = cls._analytic(
            "departments", "T89380", "Central Treasury", cls.dept_central
        )
        cls.dept_faculty = cls._analytic("departments", "T05", "Faculty")

        cls.source_gov = cls._analytic("sources", "T1", "Government Budget")
        cls.source_other = cls._analytic("sources", "T2", "Own Revenue")

        cls.fund_central = cls._analytic("funds", "T0100", "General Fund")
        cls.fund_faculty = cls._analytic("funds", "T0600", "Fixed Asset Fund")

        cls.act_sector = cls._analytic("activities", "09", "Sector")
        cls.act_program = cls._analytic(
            "activities", "09007", "Program", cls.act_sector
        )
        cls.act_main = cls._analytic(
            "activities", "090070101", "Main", cls.act_program
        )
        cls.act_secondary = cls._analytic(
            "activities", "09007010110", "Secondary", cls.act_main
        )
        cls.act_sub = cls._analytic(
            "activities", "09007010110170", "Sub", cls.act_secondary
        )

        cls.fiscal_year = cls.env["account.fiscal.year"].create(
            {
                "name": "FY-HANDOVER",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": cls.company.id,
            }
        )

        cls.bank_account = cls._account("THAND-BANK", "asset_cash")
        cls.revenue_account = cls._account("THAND-REV", "income")
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.jv_journal = cls.env.ref("account_kmitl.journal_jv")

        cls.funding = cls.env["kmitl.central.funding"].create(
            {
                "source_analytic_id": cls.source_gov.id,
                "account_fiscal_year_id": cls.fiscal_year.id,
                "bank_account_id": cls.bank_account.id,
                "revenue_account_id": cls.revenue_account.id,
                "central_department_analytic_id": cls.dept_central.id,
                "central_fund_analytic_id": cls.fund_central.id,
                "central_activity_level": "11",
                "journal_id": cls.jv_journal.id,
                "company_id": cls.company.id,
            }
        )

        cls.product = cls.env["product.product"].create(
            {"name": "Handover Service", "type": "service"}
        )
        cls.payee = cls.env["res.partner"].create(
            {
                "name": "Handover Payee",
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.payee_two = cls.env["res.partner"].create(
            {
                "name": "Handover Payee 2",
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    # ------------------------------------------------------------------
    # Fixture helpers
    # ------------------------------------------------------------------
    @classmethod
    def _analytic(cls, plan_code, code, name, parent=None):
        return cls.Analytic.create(
            {
                "name": name,
                "code": code,
                "plan_id": cls.plans[plan_code].id,
                "parent_id": parent.id if parent else False,
            }
        )

    @classmethod
    def _account(cls, code, account_type):
        return cls.env["account.account"].create(
            {
                "name": code,
                "code": code,
                "account_type": account_type,
                "company_id": cls.company.id,
            }
        )

    def _distribution(self, department, fund, activity, source=None):
        accounts = department | fund | activity | (source or self.source_gov)
        return {str(account.id): 100.0 for account in accounts}

    def _request(
        self,
        department=None,
        fund=None,
        activity=None,
        source=None,
        payees=None,
        price=1000.0,
    ):
        distribution = self._distribution(
            department or self.dept_faculty,
            fund or self.fund_faculty,
            activity or self.act_sub,
            source,
        )
        payees = payees or [self.payee]
        request = self.env["disbursement.request"].create(
            {
                "date": "2026-01-15",
                "partner_type": "multi",
                "analytic_distribution": distribution,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": payee.id,
                            "product_id": self.product.id,
                            "name": "Handover Service",
                            "quantity": 1,
                            "price_unit": price,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": distribution,
                        },
                    )
                    for payee in payees
                ],
            }
        )
        request.state = "approved"
        return request

    @staticmethod
    def _dims(line):
        return set(line.analytic_distribution or {})

    # ------------------------------------------------------------------
    # The entry
    # ------------------------------------------------------------------
    def test_handover_mirrors_both_sides(self):
        request = self._request()
        request.action_create_bill()

        handover = request.cash_revenue_handover_move_ids
        self.assertEqual(len(handover), 1)
        self.assertEqual(handover.state, "draft")
        self.assertEqual(handover.move_type, "entry")
        self.assertEqual(handover.journal_id, self.jv_journal)
        self.assertEqual(handover.date, request.date)

        lines = handover.line_ids
        self.assertEqual(len(lines), 4)
        self.assertEqual(sum(lines.mapped("debit")), 2000.0)
        self.assertEqual(sum(lines.mapped("credit")), 2000.0)

        central = self._distribution(
            self.dept_central, self.fund_central, self.act_secondary
        )
        unit = request.analytic_distribution

        bank_credit = lines.filtered(
            lambda l: l.account_id == self.bank_account and l.credit
        )
        revenue_debit = lines.filtered(
            lambda l: l.account_id == self.revenue_account and l.debit
        )
        revenue_credit = lines.filtered(
            lambda l: l.account_id == self.revenue_account and l.credit
        )
        bank_debit = lines.filtered(
            lambda l: l.account_id == self.bank_account and l.debit
        )
        for line in (bank_credit, revenue_debit, revenue_credit, bank_debit):
            self.assertEqual(len(line), 1)
            self.assertEqual(line.debit or line.credit, 1000.0)

        # Central gives up the cash and the revenue it had recognised …
        self.assertEqual(self._dims(bank_credit), set(central))
        self.assertEqual(self._dims(revenue_debit), set(central))
        # … and the unit recognises both under its own dimensions.
        self.assertEqual(self._dims(revenue_credit), set(unit))
        self.assertEqual(self._dims(bank_debit), set(unit))
        # The two sides really differ, and only in the dimensions they should.
        self.assertNotEqual(set(central), set(unit))
        self.assertIn(str(self.source_gov.id), central)
        self.assertIn(str(self.source_gov.id), unit)

    def test_header_distribution_stays_empty(self):
        """A header distribution is propagated onto every line by
        ``accounting_kmitl``, which would collapse the two sides into one."""
        request = self._request()
        request.action_create_bill()
        self.assertFalse(request.cash_revenue_handover_move_ids.analytic_distribution)

    def test_amount_is_the_gross_request_total(self):
        request = self._request(price=1234.56, payees=[self.payee, self.payee_two])
        request.action_create_bill()
        handover = request.cash_revenue_handover_move_ids
        self.assertEqual(len(handover), 1, "one handover per request, not per payee")
        self.assertEqual(
            sum(handover.line_ids.mapped("debit")), request.amount_total * 2
        )

    # ------------------------------------------------------------------
    # Central activity roll-up
    # ------------------------------------------------------------------
    def test_activity_rolls_up_to_the_configured_level(self):
        request = self._request(activity=self.act_sub)
        request.action_create_bill()
        central_line = request.cash_revenue_handover_move_ids.line_ids.filtered(
            lambda l: l.account_id == self.bank_account and l.credit
        )
        self.assertIn(str(self.act_secondary.id), central_line.analytic_distribution)

    def test_activity_at_the_level_is_left_alone(self):
        request = self._request(activity=self.act_secondary)
        request.action_create_bill()
        central_line = request.cash_revenue_handover_move_ids.line_ids.filtered(
            lambda l: l.account_id == self.bank_account and l.credit
        )
        self.assertIn(str(self.act_secondary.id), central_line.analytic_distribution)

    def test_activity_above_the_level_is_left_alone(self):
        """A coarser activity than central's level must not be pushed deeper."""
        request = self._request(activity=self.act_program)
        request.action_create_bill()
        central_line = request.cash_revenue_handover_move_ids.line_ids.filtered(
            lambda l: l.account_id == self.bank_account and l.credit
        )
        self.assertIn(str(self.act_program.id), central_line.analytic_distribution)

    # ------------------------------------------------------------------
    # Skips
    # ------------------------------------------------------------------
    def test_no_profile_no_handover(self):
        request = self._request(source=self.source_other)
        request.action_create_bill()
        self.assertFalse(request.cash_revenue_handover_move_ids)
        self.assertTrue(request.bill_ids, "the bill is still raised")

    def test_central_department_gets_no_handover(self):
        request = self._request(department=self.dept_central)
        request.action_create_bill()
        self.assertFalse(request.cash_revenue_handover_move_ids)

    def test_department_under_central_gets_no_handover(self):
        request = self._request(department=self.dept_central_child)
        request.action_create_bill()
        self.assertFalse(request.cash_revenue_handover_move_ids)

    def test_handover_is_created_once(self):
        request = self._request()
        request.action_create_bill()
        request._create_cash_revenue_handover()
        self.assertEqual(len(request.cash_revenue_handover_move_ids), 1)

    # ------------------------------------------------------------------
    # Decoupling
    # ------------------------------------------------------------------
    def test_handover_is_not_one_of_the_bills(self):
        """Sharing ``disbursement_request_id`` would make the handover a bill:
        bill creation would refuse, and posting it would advance the request."""
        request = self._request()
        request.action_create_bill()
        handover = request.cash_revenue_handover_move_ids
        self.assertFalse(handover.disbursement_request_id)
        self.assertNotIn(handover, request.bill_ids)
        self.assertEqual(request.bill_count, 1)

    def test_posting_the_handover_leaves_the_request_alone(self):
        request = self._request()
        request.action_create_bill()
        request.cash_revenue_handover_move_ids.action_post()
        self.assertEqual(request.state, "approved")

    def test_cancelling_the_request_leaves_the_handover_standing(self):
        request = self._request()
        request.action_create_bill()
        handover = request.cash_revenue_handover_move_ids
        request.action_cancel()
        self.assertEqual(request.state, "cancel")
        self.assertEqual(handover.state, "draft")

    def test_handover_touches_no_budget(self):
        request = self._request()
        before = self.env["budget.move"].search_count([])
        request.action_create_bill()
        self.assertEqual(self.env["budget.move"].search_count([]), before)

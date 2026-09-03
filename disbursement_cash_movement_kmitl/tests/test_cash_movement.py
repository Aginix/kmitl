# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCashMovement(TransactionCase):
    """The inter-account cash-movement legs a disbursement voucher grows on
    its way to a paying account (หัวจ่าย).

    Routing is exercised against the 18 routes ``post_init_hook`` seeds, not
    against hand-made ones, so these tests also stand as a check on the seed
    data itself.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Payment = cls.env["account.payment"]
        cls.Route = cls.env["kmitl.cash.route"]
        cls.Account = cls.env["account.account"]

        Plan = cls.env["account.analytic.plan"]
        Analytic = cls.env["account.analytic.account"]

        def plan(code):
            return Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": code.title(), "code": code}
            )

        cls.dept_account = Analytic.create(
            {"name": "Dept test", "plan_id": plan("departments").id}
        )
        cls.fund_account = Analytic.create(
            {"name": "Fund test", "plan_id": plan("funds").id}
        )
        cls.activity_account = Analytic.create(
            {"name": "Activity test", "plan_id": plan("activities").id}
        )

        # The real seeded sources: this module's routes are keyed on these
        # exact records, so routing has to be proven against them.
        cls.source_rev = cls.env.ref("account_analytic_kmitl.source_2")
        cls.source_gov = cls.env.ref("account_analytic_kmitl.source_1")
        cls.source_unrouted = Analytic.create(
            {"name": "Unrouted Source", "plan_id": cls.source_rev.plan_id.id}
        )

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
        cls.purchase_journal = cls.env.ref("account_kmitl.journal_ap")
        cls.product = cls.env["product.product"].create(
            {"name": "Service", "type": "service"}
        )

        # Seeded paying accounts (หัวจ่าย) — KTB is on 4 of the 18 routes (a
        # different hop chain for REV and for GOV), cash and the REV/GOV
        # savings accounts are the "no route expected" cases.
        cls.ktb_line = cls.env.ref("account_kmitl.paying_account_1112120002_transfer")
        cls.cash_line = cls.env.ref("account_kmitl.paying_account_1111000002_cash")
        cls.scb_direct_line = cls.env.ref(
            "account_kmitl.paying_account_1112210004_transfer"
        )
        cls.subject = cls.env.ref("finance_kmitl.payment_subject_company_revenue")

        cls.payee = cls.env["res.partner"].create(
            {
                "name": "Cash Movement Payee",
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    # ------------------------------------------------------------------
    # Fixture helpers
    # ------------------------------------------------------------------
    def _distribution(self, source):
        accounts = (
            self.dept_account | self.fund_account | self.activity_account | source
        )
        return {str(account.id): 100.0 for account in accounts}

    def _paid(self, source, paying_line, price=1000.0):
        """A payment authorised from a real disbursement request, drawn on
        ``paying_line`` and carrying ``source`` as its แหล่งเงิน — the same
        route lookup a real voucher goes through in production."""
        distribution = self._distribution(source)
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
                            "partner_id": self.payee.id,
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": price,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": distribution,
                        },
                    )
                ],
            }
        )
        request.state = "approved"
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.payee.id,
                "invoice_date": "2026-01-15",
                "journal_id": self.purchase_journal.id,
                "disbursement_request_id": request.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": price,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": distribution,
                        },
                    )
                ],
            }
        )
        bill.action_post()
        request.payment_subject_id = self.subject
        request.payment_line_ids.write(
            {"paying_account_id": paying_line.id, "paying_account_match": "manual"}
        )
        request.action_audit()
        request.action_authorize()
        return request.payment_ids

    # ------------------------------------------------------------------
    # 1. Seed data
    # ------------------------------------------------------------------
    def test_all_18_routes_are_seeded(self):
        self.assertEqual(len(self.Route.search([])), 18)

    def test_ktb_rev_route_hops(self):
        route = self.env.ref("disbursement_cash_movement_kmitl.route_1112120002_rev")
        self.assertEqual(
            route.hop_ids.sorted("sequence").account_id.mapped("code"),
            ["1112210004", "1112220015"],
        )

    def test_new_paying_account_gov_route_chains_through_the_rev_hop(self):
        route = self.env.ref("disbursement_cash_movement_kmitl.route_1112220016_gov")
        self.assertEqual(
            route.hop_ids.sorted("sequence").account_id.mapped("code"),
            ["1112110012", "1112120025", "1112210001"],
        )

    def test_direct_routes_have_no_hops(self):
        rev_direct = self.env.ref(
            "disbursement_cash_movement_kmitl.route_1112210004_rev_direct"
        )
        gov_direct = self.env.ref(
            "disbursement_cash_movement_kmitl.route_1112110012_gov_direct"
        )
        self.assertFalse(rev_direct.hop_ids)
        self.assertFalse(gov_direct.hop_ids)

    # ------------------------------------------------------------------
    # 2. Amounts
    # ------------------------------------------------------------------
    def test_legs_reuse_the_liquidity_lines_net_amount(self):
        payment = self._paid(self.source_rev, self.ktb_line, price=1000.0)
        vals = payment._prepare_move_line_default_vals()
        liquidity, counterpart = vals[0], vals[1]
        movement = [v for v in vals[2:] if v.get("is_cash_movement_line")]
        self.assertEqual(len(movement), 4)
        self.assertEqual(
            sum(v["debit"] for v in movement), sum(v["credit"] for v in movement)
        )
        paying_leg = [
            v
            for v in movement
            if v["account_id"] == self.ktb_line.payment_account_id.id
        ]
        self.assertEqual(len(paying_leg), 1)
        self.assertEqual(paying_leg[0]["debit"], liquidity["credit"])
        self.assertEqual(counterpart["debit"], 1000.0)

    def test_prepare_move_line_default_vals_keeps_wht_and_appends_legs(self):
        """finance_kmitl's withholding-tax preservation and this module's legs
        compose: one substitutes the write-off dicts, the other appends
        after."""
        payment = self._paid(self.source_rev, self.ktb_line)
        wht = self.env["account.withholding.tax"].search([], limit=1)
        self.assertTrue(wht, "the KMITL chart seeds the withholding taxes")
        vals = payment._write_off_line_vals(payment.move_id.line_ids[:1])
        stashed = [dict(vals, wht_tax_id=wht.id, tax_base_amount=1000.0)]
        prepared = payment.with_context(
            kmitl_preserved_write_off={payment.id: stashed}
        )._prepare_move_line_default_vals()
        self.assertEqual(prepared[2]["wht_tax_id"], wht.id)
        movement = [v for v in prepared if v.get("is_cash_movement_line")]
        self.assertEqual(len(movement), 4)

    # ------------------------------------------------------------------
    # 3. Dimensions
    # ------------------------------------------------------------------
    def test_legs_carry_the_same_dimensions_as_the_voucher(self):
        payment = self._paid(self.source_rev, self.ktb_line)
        distribution = payment.analytic_distribution
        movement = payment.move_id.line_ids.filtered("is_cash_movement_line")
        self.assertTrue(movement)
        for line in movement:
            self.assertEqual(line.analytic_distribution, distribution)

    def test_legs_follow_a_dimension_edit_after_creation(self):
        payment = self._paid(self.source_rev, self.ktb_line)
        new_department = self.env["account.analytic.account"].create(
            {"name": "New Dept", "plan_id": self.dept_account.plan_id.id}
        )
        new_distribution = dict(payment.analytic_distribution)
        del new_distribution[str(self.dept_account.id)]
        new_distribution[str(new_department.id)] = 100.0
        payment.write({"analytic_distribution": new_distribution})
        movement = payment.move_id.line_ids.filtered("is_cash_movement_line")
        self.assertTrue(movement)
        for line in movement:
            self.assertEqual(line.analytic_distribution, new_distribution)

    # ------------------------------------------------------------------
    # 4. Core sync survives a rebuild
    # ------------------------------------------------------------------
    def test_resync_does_not_leave_a_ghost_writeoff_line(self):
        """A payment with a route but no withholding tax must not gain a
        bogus zero-amount line when a trigger field forces core to rebuild
        the entry (e.g. finance correcting the payee's bank afterwards)."""
        payment = self._paid(self.source_rev, self.ktb_line)
        self.assertEqual(
            len(payment.move_id.line_ids.filtered("is_cash_movement_line")), 4
        )
        bank = self.env["res.partner.bank"].create(
            {"partner_id": self.payee.id, "acc_number": "TEST-RESYNC-001"}
        )
        payment.partner_bank_id = bank.id
        lines = payment.move_id.line_ids
        self.assertEqual(len(lines.filtered("is_cash_movement_line")), 4)
        self.assertEqual(len(lines), 6, "no stray write-off line survived the rebuild")
        self.assertEqual(sum(lines.mapped("debit")), sum(lines.mapped("credit")))

    # ------------------------------------------------------------------
    # 5. Zero hops / no route at all
    # ------------------------------------------------------------------
    def test_direct_paying_account_has_no_legs_and_no_warning(self):
        payment = self._paid(self.source_rev, self.scb_direct_line)
        self.assertFalse(payment.move_id.line_ids.filtered("is_cash_movement_line"))
        exception_ids = payment.move_id.detect_exceptions()
        rule = self.env.ref(
            "disbursement_cash_movement_kmitl.excep_cash_route_not_found"
        )
        self.assertNotIn(rule.id, exception_ids)

    def test_no_route_row_has_no_legs_but_flags_the_exception(self):
        payment = self._paid(self.source_unrouted, self.ktb_line)
        self.assertFalse(payment.move_id.line_ids.filtered("is_cash_movement_line"))
        exception_ids = payment.move_id.detect_exceptions()
        rule = self.env.ref(
            "disbursement_cash_movement_kmitl.excep_cash_route_not_found"
        )
        self.assertIn(rule.id, exception_ids)

    # ------------------------------------------------------------------
    # 6. Cash
    # ------------------------------------------------------------------
    def test_cash_payment_has_no_legs_and_no_warning(self):
        payment = self._paid(self.source_rev, self.cash_line)
        self.assertFalse(payment.move_id.line_ids.filtered("is_cash_movement_line"))
        exception_ids = payment.move_id.detect_exceptions()
        rule = self.env.ref(
            "disbursement_cash_movement_kmitl.excep_cash_route_not_found"
        )
        self.assertNotIn(rule.id, exception_ids)

    # ------------------------------------------------------------------
    # 7. Scope: only vouchers born from a disbursement request
    # ------------------------------------------------------------------
    def test_payment_without_disbursement_request_has_no_legs(self):
        payment = self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
                "amount": 500.0,
                "journal_id": self.ktb_line.journal_id.id,
                "payment_method_line_id": self.ktb_line.id,
                "analytic_distribution": self._distribution(self.source_rev),
            }
        )
        self.assertFalse(payment.move_id.line_ids.filtered("is_cash_movement_line"))

    # ------------------------------------------------------------------
    # 8. Posted voucher balances
    # ------------------------------------------------------------------
    def test_intermediate_and_paying_accounts_net_to_zero_once_posted(self):
        payment = self._paid(self.source_rev, self.ktb_line, price=1000.0)
        payment.move_id.action_submit()
        payment.move_id.action_post()
        lines = payment.move_id.line_ids
        self.assertEqual(sum(lines.mapped("debit")), sum(lines.mapped("credit")))
        cheque_account = self.Account.search(
            [("code", "=", "1112220015"), ("company_id", "=", self.company.id)],
            limit=1,
        )
        for account in (self.ktb_line.payment_account_id, cheque_account):
            account_lines = lines.filtered(lambda l, a=account: l.account_id == a)
            self.assertAlmostEqual(
                sum(account_lines.mapped("debit"))
                - sum(account_lines.mapped("credit")),
                0.0,
                msg="%s does not net to zero" % account.display_name,
            )

    def test_gov_source_uses_the_gov_hop_chain(self):
        payment = self._paid(self.source_gov, self.ktb_line)
        movement = payment.move_id.line_ids.filtered("is_cash_movement_line")
        self.assertEqual(
            set(movement.account_id.mapped("code")),
            {"1112110012", "1112120025", "1112120002"},
        )

    # ------------------------------------------------------------------
    # 9. Constraints
    # ------------------------------------------------------------------
    def test_duplicate_source_on_same_paying_account_raises(self):
        with self.assertRaises(ValidationError):
            self.Route.create(
                {
                    "paying_gl_account_id": self.ktb_line.payment_account_id.id,
                    "source_analytic_ids": [(6, 0, [self.source_rev.id])],
                    "company_id": self.company.id,
                }
            )

    def test_paying_account_as_its_own_hop_raises(self):
        ktb_gl = self.ktb_line.payment_account_id
        with self.assertRaises(ValidationError):
            self.Route.create(
                {
                    "paying_gl_account_id": ktb_gl.id,
                    "source_analytic_ids": [(6, 0, [self.source_unrouted.id])],
                    "company_id": self.company.id,
                    "hop_ids": [(0, 0, {"account_id": ktb_gl.id})],
                }
            )

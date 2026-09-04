# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import AccessError, ValidationError
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

    def _billed_line(self, source, price=1000.0):
        """A payment line at ``bills_posted``, before any ``account.payment``
        exists — the exact point the auditor is choosing a paying account,
        which is what the live preview has to work from."""
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
        return request.payment_line_ids

    def _paid(self, source, paying_line, price=1000.0):
        """A payment authorised from a real disbursement request, drawn on
        ``paying_line`` and carrying ``source`` as its แหล่งเงิน — the same
        route lookup a real voucher goes through in production."""
        line = self._billed_line(source, price)
        line.write(
            {"paying_account_id": paying_line.id, "paying_account_match": "manual"}
        )
        line.request_id.action_audit()
        line.request_id.action_authorize()
        return line.request_id.payment_ids

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

    def test_is_missing_cash_route_only_flags_a_real_setup_gap(self):
        """The rule's own ``code`` field is a single call to this.

        ``safe_eval`` hands that field a bare context — ``self``/``object``/
        ``obj`` and no ``env`` — so everything that decides the answer has to
        live here, where it is linted and covered.
        """
        gap = self._paid(self.source_unrouted, self.ktb_line)
        self.assertTrue(gap.move_id._is_missing_cash_route())
        routed = self._paid(self.source_rev, self.ktb_line)
        self.assertFalse(routed.move_id._is_missing_cash_route())
        # A move that is no voucher at all cannot be missing a route.
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-01-15",
                "journal_id": self.env.ref("account_kmitl.journal_jv").id,
            }
        )
        self.assertFalse(entry._is_missing_cash_route())

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

    # ------------------------------------------------------------------
    # 10. Payment-line preview
    # ------------------------------------------------------------------
    def test_preview_updates_live_before_any_payment_exists(self):
        """The auditor sees the route change the moment they pick a
        different paying account — no payment created yet, nothing saved."""
        line = self._billed_line(self.source_rev)
        # payment_subject_company_revenue is a fixed (non auto-matching)
        # subject, so choosing it already defaulted every row onto its own
        # paying account — the 0-hop direct route for this source.
        self.assertEqual(line.paying_account_id, self.scb_direct_line)
        self.assertEqual(line.cash_route_state, "direct")
        line.paying_account_id = self.ktb_line.id
        self.assertEqual(line.cash_route_state, "routed")
        self.assertIn("→", line.cash_route_display)
        line.paying_account_id = self.scb_direct_line.id
        self.assertEqual(line.cash_route_state, "direct")

    def test_preview_shows_direct_for_a_zero_hop_route(self):
        payment = self._paid(self.source_rev, self.scb_direct_line)
        line = payment.disbursement_request_id.payment_line_ids
        self.assertEqual(line.cash_route_state, "direct")
        self.assertEqual(line.cash_route_display, "SCB 11066-5")

    def test_preview_shows_missing_when_no_route_is_set_up(self):
        payment = self._paid(self.source_unrouted, self.ktb_line)
        line = payment.disbursement_request_id.payment_line_ids
        self.assertEqual(line.cash_route_state, "missing")
        self.assertFalse(line.cash_route_display)

    def test_preview_is_blank_for_cash(self):
        payment = self._paid(self.source_rev, self.cash_line)
        line = payment.disbursement_request_id.payment_line_ids
        self.assertFalse(line.cash_route_state)
        self.assertFalse(line.cash_route_display)

    def test_preview_follows_the_source_not_only_the_paying_account(self):
        rev_line = self._billed_line(self.source_rev)
        rev_line.paying_account_id = self.ktb_line.id
        gov_line = self._billed_line(self.source_gov)
        gov_line.paying_account_id = self.ktb_line.id
        self.assertNotEqual(rev_line.cash_route_display, gov_line.cash_route_display)

    def test_preview_state_matches_the_exception_helper(self):
        """The badge shown while still choosing a paying account and the
        non-blocking warning at Submit share one definition
        (``kmitl.cash.route._should_have_route``), so they cannot disagree."""
        missing = self._paid(self.source_unrouted, self.ktb_line)
        missing_line = missing.disbursement_request_id.payment_line_ids
        self.assertEqual(missing_line.cash_route_state, "missing")
        self.assertTrue(missing.move_id._is_missing_cash_route())

        routed = self._paid(self.source_rev, self.ktb_line)
        routed_line = routed.disbursement_request_id.payment_line_ids
        self.assertEqual(routed_line.cash_route_state, "routed")
        self.assertFalse(routed.move_id._is_missing_cash_route())

        cash = self._paid(self.source_rev, self.cash_line)
        cash_line = cash.disbursement_request_id.payment_line_ids
        self.assertFalse(cash_line.cash_route_state)
        self.assertFalse(cash.move_id._is_missing_cash_route())

    def test_preview_is_readable_by_the_auditor_group_alone(self):
        """``disbursement.payment.line``'s new fields are ``compute_sudo``:
        the auditor holds no ACL on ``kmitl.cash.route`` at all, so a plain
        (non-sudo) compute would raise the moment this tab opened."""
        line = self._billed_line(self.source_rev)
        line.paying_account_id = self.ktb_line.id
        auditor_group = self.env.ref(
            "disbursement_finance_kmitl.group_disbursement_payment_auditor"
        )
        auditor = (
            self.env["res.users"]
            .with_context(no_reset_password=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Cash Route Auditor Test",
                    "login": "cash_movement_auditor_test",
                    "groups_id": [
                        (6, 0, [self.env.ref("base.group_user").id, auditor_group.id])
                    ],
                }
            )
        )
        with self.assertRaises(AccessError):
            self.Route.with_user(auditor).search([])
        self.assertEqual(line.with_user(auditor).cash_route_state, "routed")

    def test_display_chain_names_every_account_by_bank_and_number(self):
        """No account in any seeded route falls back to its bare GL code —
        every one has an institute bank account linked and a named bank."""
        for route in self.Route.search([]):
            for account in route._path_accounts():
                self.assertTrue(
                    account.kmitl_bank_account_id,
                    "%s (%s) has no institute bank account linked"
                    % (account.code, route.display_name),
                )
                self.assertTrue(
                    account.kmitl_bank_account_id.bank_id.short_name,
                    "%s (%s)'s bank has no short name"
                    % (account.code, route.display_name),
                )

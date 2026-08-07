# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentWorkflow(TransactionCase):
    """Post-bill payment-execution workflow: state machine, guards, and the
    payee-level paying account.

    The pre-bill approval (with budget) is exercised by ``finance_kmitl_demo``;
    here the bills are made directly and posted, which is what carries the
    request into ``bills_posted`` and makes the payment lines.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # The 4 required analytic dimensions so the request can leave draft.
        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]
        cls.distribution = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = Plan.search([("code", "=", code)], limit=1)
            if not plan:
                plan = Plan.create({"name": code.title(), "code": code})
            account = Account.create({"name": "%s test" % code, "plan_id": plan.id})
            cls.distribution[str(account.id)] = 100

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
            {
                "name": "Service",
                "type": "service",
            }
        )

        # Seeded paying accounts (หัวจ่าย) on ใบสำคัญจ่าย.
        cls.scb_account = cls.env.ref("account_kmitl.paying_account_1112210004")
        cls.ktb_account = cls.env.ref("account_kmitl.paying_account_1112120002")
        cls.cheque_account = cls.env.ref("account_kmitl.paying_account_1112220015")
        cls.cash_account = cls.env.ref("account_kmitl.paying_account_1111000002")

        cls.subject_vendor = cls.env.ref("finance_kmitl.payment_subject_vendor_direct")
        cls.subject_advance = cls.env.ref(
            "finance_kmitl.payment_subject_advance_reimburse"
        )

        # A payee banking with KTB, and one banking nowhere the institute does.
        cls.payee_ktb = cls._make_payee("Payee KTB", cls.ktb_account.bank_id)
        other_bank = cls.env["res.bank"].create(
            {"name": "Some Other Bank", "bic": "OTHRTHBK"}
        )
        cls.payee_other = cls._make_payee("Payee Other", other_bank)

    @classmethod
    def _make_payee(cls, name, bank):
        partner = cls.env["res.partner"].create(
            {
                "name": name,
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "partner_id": partner.id,
                "acc_number": "TEST-%s" % name.replace(" ", "-"),
                "bank_id": bank.id,
            }
        )
        return partner

    # ------------------------------------------------------------------
    def _make_request(self, payees=None):
        payees = payees or [self.payee_ktb]
        return self.env["disbursement.request"].create(
            {
                "date": "2026-01-15",
                "partner_type": "multi",
                "analytic_distribution": self.distribution,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": payee.id,
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                    for payee in payees
                ],
            }
        )

    def _post_bills(self, request, payees):
        """Post one vendor bill per payee, which carries the request into
        ``bills_posted`` exactly as the accounting bridge does in production."""
        request.state = "approved"
        for payee in payees:
            bill = self.env["account.move"].create(
                {
                    "move_type": "in_invoice",
                    "partner_id": payee.id,
                    "partner_bank_id": payee.bank_ids[:1].id,
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
                                "price_unit": 1000.0,
                                "account_id": self.expense_account.id,
                                "analytic_distribution": self.distribution,
                            },
                        )
                    ],
                }
            )
            bill.action_post()
        self.assertEqual(request.state, "bills_posted")
        return request

    def _billed_request(self, payees=None, subject=None):
        payees = payees or [self.payee_ktb]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        request.payment_subject_id = subject or self.subject_vendor
        return request

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------
    def test_paying_accounts_are_seeded_with_their_bank(self):
        journal = self.env.ref("account_kmitl.journal_pv")
        paying = journal.outbound_payment_method_line_ids.filtered("payment_account_id")
        self.assertEqual(len(paying), 8)
        banked = paying.filtered(lambda a: a.payment_method_id.code != "kmitl_cash")
        self.assertTrue(all(banked.mapped("bank_account_id")))
        # Cash books against cash on hand, not against a bank.
        self.assertFalse(self.cash_account.bank_account_id)
        self.assertEqual(self.cash_account.payment_account_id.code, "1111000002")

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def test_audit_authorize_forward(self):
        request = self._billed_request()
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        request.action_authorize()
        self.assertEqual(request.state, "payment_authorized")

    def test_audit_requires_bills_posted(self):
        request = self._billed_request()
        request.action_audit()  # -> payment_audited
        with self.assertRaises(UserError):
            request.action_audit()  # wrong source state

    def test_authorize_requires_audited(self):
        request = self._billed_request()
        with self.assertRaises(UserError):
            request.action_authorize()  # still bills_posted

    def test_confirm_paid_requires_payment(self):
        request = self._billed_request()
        request.action_audit()
        request.action_authorize()
        with self.assertRaises(UserError):
            request.action_confirm_paid()

    def test_pipeline_done_when_cleared(self):
        request = self._billed_request()
        request.state = "cleared"
        self.assertEqual(request.pipeline_status, "done")

    def test_cancel_blocked_after_audit_when_billed(self):
        request = self._billed_request()
        request.action_audit()
        request.action_authorize()
        request.state = "paid"
        with self.assertRaises(UserError):
            request.action_cancel()

    # ------------------------------------------------------------------
    # Payment lines
    # ------------------------------------------------------------------
    def test_one_payment_line_per_payee(self):
        request = self._billed_request([self.payee_ktb, self.payee_other])
        self.assertEqual(len(request.payment_line_ids), 2)
        self.assertEqual(
            request.payment_line_ids.mapped("partner_id"),
            self.payee_ktb + self.payee_other,
        )

    def test_ensure_payment_lines_is_idempotent(self):
        request = self._billed_request()
        request._ensure_payment_lines()
        request._ensure_payment_lines()
        self.assertEqual(len(request.payment_line_ids), 1)

    def test_amounts_come_from_the_bill(self):
        request = self._billed_request()
        line = request.payment_line_ids
        self.assertEqual(line.amount_bill, 1000.0)
        self.assertEqual(line.amount_net, 1000.0 - line.amount_wht)

    # ------------------------------------------------------------------
    # Paying account derivation
    # ------------------------------------------------------------------
    def test_fixed_subject_pays_everyone_from_the_main_account(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_vendor
        )
        lines = request.payment_line_ids
        self.assertEqual(
            set(lines.mapped("paying_account_id").ids), {self.scb_account.id}
        )
        self.assertEqual(set(lines.mapped("paying_account_match")), {"main"})

    def test_auto_match_serves_a_payee_from_their_own_bank(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_advance
        )
        by_payee = {line.partner_id: line for line in request.payment_line_ids}
        self.assertEqual(by_payee[self.payee_ktb].paying_account_id, self.ktb_account)
        self.assertEqual(by_payee[self.payee_ktb].paying_account_match, "bank")
        # Nobody banks there: falls back to the subject's account.
        self.assertEqual(by_payee[self.payee_other].paying_account_id, self.scb_account)
        self.assertEqual(by_payee[self.payee_other].paying_account_match, "fallback")

    def test_a_hand_picked_account_survives_re_derivation(self):
        request = self._billed_request([self.payee_ktb], self.subject_advance)
        line = request.payment_line_ids
        line.write(
            {
                "paying_account_id": self.cheque_account.id,
                "paying_account_match": "manual",
            }
        )
        request.payment_subject_id = self.subject_vendor
        self.assertEqual(line.paying_account_id, self.cheque_account)
        self.assertEqual(line.paying_account_match, "manual")

    def test_method_follows_the_paying_account(self):
        request = self._billed_request([self.payee_ktb], self.subject_advance)
        line = request.payment_line_ids
        line.paying_account_id = self.cheque_account
        self.assertEqual(line.payment_method_id.code, "kmitl_cheque")

    # ------------------------------------------------------------------
    # Audit guards
    # ------------------------------------------------------------------
    def test_audit_needs_a_subject(self):
        payees = [self.payee_ktb]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        with self.assertRaises(UserError):
            request.action_audit()

    def test_audit_refuses_a_transfer_payee_without_a_bank_account(self):
        payee = self.env["res.partner"].create(
            {
                "name": "Bankless",
                "property_account_payable_id": self.payable_account.id,
            }
        )
        payees = [payee]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        request.payment_subject_id = self.subject_vendor
        with self.assertRaises(UserError):
            request.action_audit()
        # Moving them onto cash unblocks it — cash needs no bank account.
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cash_account.id,
                "paying_account_match": "manual",
            }
        )
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")

    # ------------------------------------------------------------------
    # Payment creation
    # ------------------------------------------------------------------
    def test_payment_carries_the_paying_account_and_its_voucher(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_advance
        )
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        by_payee = {p.partner_id: p for p in request.payment_ids}
        self.assertEqual(
            by_payee[self.payee_ktb].payment_method_line_id, self.ktb_account
        )
        self.assertEqual(
            by_payee[self.payee_ktb].journal_id, self.ktb_account.journal_id
        )
        self.assertEqual(
            by_payee[self.payee_other].payment_method_line_id, self.scb_account
        )
        self.assertEqual(
            request.payment_line_ids.mapped("payment_id"), request.payment_ids
        )

    def test_banking_coordinates_freeze_once_the_payment_exists(self):
        request = self._billed_request([self.payee_ktb], self.subject_vendor)
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        with self.assertRaises(UserError):
            request.payment_line_ids.paying_account_id = self.ktb_account

    def test_cash_payment_skips_the_bank_export_gate(self):
        request = self._billed_request([self.payee_ktb], self.subject_vendor)
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cash_account.id,
                "paying_account_match": "manual",
            }
        )
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        payment = request.payment_ids
        self.assertFalse(payment.needs_bank_export)


@tagged("post_install", "-at_install")
class TestPaymentSubject(TransactionCase):
    """The subject's own derivation, away from a disbursement."""

    def test_fallback_is_used_when_no_allowed_account_matches(self):
        subject = self.env.ref("finance_kmitl.payment_subject_advance_reimburse")
        other_bank = self.env["res.bank"].create(
            {"name": "Nowhere Bank", "bic": "NWHRTHBK"}
        )
        account, match = subject._paying_account_with_match(other_bank)
        self.assertEqual(account, subject.default_paying_account_id)
        self.assertEqual(match, "fallback")

    def test_a_fixed_subject_reports_its_account_as_main(self):
        subject = self.env.ref("finance_kmitl.payment_subject_vendor_direct")
        account, match = subject._paying_account_with_match(self.env["res.bank"])
        self.assertEqual(account, subject.default_paying_account_id)
        self.assertEqual(match, "main")

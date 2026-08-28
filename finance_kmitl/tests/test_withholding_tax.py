# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWithholdingTaxOnTheVoucher(TransactionCase):
    """Withholding declared on a voucher the finance office filled in itself.

    Everything here is about a voucher with no bill behind it — the one kind that
    had nowhere to say what it withheld. The last test is the other kind, and it
    is a regression: a voucher raised from a disbursement carries its withholding
    on the entry and must keep reading it from there.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Payment = cls.env["account.payment"]
        cls.Cert = cls.env["withholding.tax.cert"]

        cls.paying_account = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )
        cls.payment_type = cls.env.ref("finance_kmitl.payment_type_normal_outbound")
        cls.other_payment_type = cls.env["kmitl.payment.type"].search(
            [
                ("direction", "=", "outbound"),
                ("id", "!=", cls.payment_type.id),
            ],
            limit=1,
        )
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        # A withholding tax of this suite's own: the two account_kmitl seeds are
        # both 1%, and a rate that divides the gross evenly would hide a rounding
        # or a base mistake rather than show it.
        cls.wht_account = cls.env["account.account"].create(
            {
                "name": "Withholding tax payable (test)",
                "code": "2120099TST",
                "account_type": "liability_current",
                "wht_account": True,
                "company_id": cls.env.company.id,
            }
        )
        cls.wht_tax = cls.env["account.withholding.tax"].create(
            {
                "name": "WHT 3% service (test)",
                "amount": 3.0,
                "account_id": cls.wht_account.id,
                "income_tax_form": "pnd53",
                "wht_cert_income_type": "5",
                "company_id": cls.env.company.id,
            }
        )
        cls.payee_type = cls.env["res.partner.type"].create(
            {
                "name": "Private company (test)",
                "company_type": "company",
                "wht_tax_id": cls.wht_tax.id,
            }
        )
        cls.payee = cls.env["res.partner"].create(
            {
                "name": "บริษัท รับเหมาบริการ จำกัด",
                "partner_type_id": cls.payee_type.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    # ------------------------------------------------------------------
    def _voucher(self, **overrides):
        """A draft voucher withholding 3% of a 10,000 gross."""
        vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.payee.id,
            "date": "2026-02-10",
            "journal_id": self.paying_account.journal_id.id,
            "payment_method_line_id": self.paying_account.id,
            "kmitl_payment_type_id": self.payment_type.id,
            "wht_tax_id": self.wht_tax.id,
            "wht_amount_base": 10000.0,
            "wht_cert_income_type": "5",
        }
        vals.update(overrides)
        return self.Payment.create(vals)

    def _billed_voucher(self):
        """The shape ``disbursement.payment.line`` produces: no rate on the
        voucher, the withholding delivered as a write-off line on its entry."""
        return self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
                "amount": 9700.0,
                "date": "2026-02-10",
                "journal_id": self.paying_account.journal_id.id,
                "payment_method_line_id": self.paying_account.id,
                "kmitl_payment_type_id": self.payment_type.id,
                "write_off_line_vals": [
                    {
                        "name": self.wht_tax.display_name,
                        "account_id": self.wht_account.id,
                        "partner_id": self.payee.id,
                        "currency_id": self.env.company.currency_id.id,
                        "amount_currency": -300.0,
                        "balance": -300.0,
                        "wht_tax_id": self.wht_tax.id,
                        "tax_base_amount": 10000.0,
                    }
                ],
            }
        )

    def _wht_lines(self, payment):
        return payment.move_id.line_ids.filtered("wht_tax_id")

    # ------------------------------------------------------------------
    # The income is the input; the amount paid follows
    # ------------------------------------------------------------------
    def test_the_income_and_the_rate_decide_the_amount_paid(self):
        payment = self._voucher()

        self.assertEqual(payment.amount_wht, 300.0)
        self.assertEqual(payment.amount, 9700.0)
        # The gross reads back as the base, from the other end of the same sum.
        self.assertEqual(payment.amount_before_wht, 10000.0)

    def test_the_amount_box_is_typed_with_the_income(self):
        """What an officer types is the figure on the invoice in their hand, not
        the figure that will leave the bank."""
        payment = self.Payment.new(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
            }
        )
        payment._onchange_partner_id_wht()

        payment.amount = 10000.0
        payment._onchange_amount_wht()

        self.assertEqual(payment.wht_amount_base, 10000.0)
        self.assertEqual(payment.amount_wht, 300.0)
        self.assertEqual(payment.amount, 9700.0)

    def test_typing_the_same_income_twice_withholds_once(self):
        """Odoo re-runs onchange methods until the form settles, so this one sees
        its own result. Without the equality test in it, each pass would withhold
        from the previous net: 10,000 -> 9,700 -> 9,409."""
        payment = self.Payment.new(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
            }
        )
        payment._onchange_partner_id_wht()
        payment.amount = 10000.0
        payment._onchange_amount_wht()

        # The second pass the web client would make, and a third for good measure.
        payment._onchange_amount_wht()
        payment._onchange_amount_wht()

        self.assertEqual(payment.wht_amount_base, 10000.0)
        self.assertEqual(payment.amount, 9700.0)

    def test_retyping_the_income_moves_both_figures(self):
        payment = self.Payment.new(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
            }
        )
        payment._onchange_partner_id_wht()
        payment.amount = 10000.0
        payment._onchange_amount_wht()

        payment.amount = 20000.0
        payment._onchange_amount_wht()

        self.assertEqual(payment.wht_amount_base, 20000.0)
        self.assertEqual(payment.amount_wht, 600.0)
        self.assertEqual(payment.amount, 19400.0)

    def test_the_base_seeds_itself_from_the_amount_already_typed(self):
        """A voucher is not filled in in one fixed order: the amount may be typed
        before the payee is known, and picking a payee who is withheld from turns
        that number into the gross rather than throwing it away."""
        payment = self.Payment.new(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
                "amount": 10000.0,
            }
        )

        payment._onchange_partner_id_wht()
        payment._onchange_wht_tax_id()

        self.assertEqual(payment.wht_tax_id, self.wht_tax)
        self.assertEqual(payment.wht_amount_base, 10000.0)
        self.assertEqual(payment.amount, 9700.0)

    def test_changing_the_base_re_derives_the_amount_and_the_entry(self):
        payment = self._voucher()

        payment.wht_amount_base = 4000.0

        self.assertEqual(payment.amount_wht, 120.0)
        self.assertEqual(payment.amount, 3880.0)
        self.assertEqual(payment.amount_before_wht, 4000.0)
        self.assertEqual(abs(self._wht_lines(payment).balance), 120.0)
        self.assertEqual(self._wht_lines(payment).tax_base_amount, 4000.0)

    def test_taking_the_rate_away_hands_the_withholding_back(self):
        """The base was what the payee was owed all along, so deciding not to
        withhold owes them the whole of it — not the net that was standing."""
        payment = self._voucher()
        self.assertEqual(payment.amount, 9700.0)

        payment.wht_tax_id = False

        self.assertEqual(payment.amount, 10000.0)
        self.assertEqual(payment.amount_wht, 0.0)
        self.assertFalse(payment.wht_amount_base)
        self.assertFalse(payment.wht_cert_income_type)
        self.assertFalse(self._wht_lines(payment))

    # ------------------------------------------------------------------
    # The entry
    # ------------------------------------------------------------------
    def test_the_entry_splits_the_gross_into_the_payment_and_the_withholding(self):
        payment = self._voucher()

        lines = payment.move_id.line_ids
        self.assertEqual(len(lines), 3)
        payable = lines.filtered(lambda line: line.account_id == self.payable_account)
        wht = self._wht_lines(payment)
        liquidity = lines - payable - wht
        self.assertEqual(payable.debit, 10000.0)
        self.assertEqual(liquidity.credit, 9700.0)
        self.assertEqual(wht.credit, 300.0)
        self.assertEqual(wht.account_id, self.wht_account)

    def test_the_withholding_line_carries_what_the_certificate_is_made_of(self):
        """``wht_tax_id`` and ``tax_base_amount`` are the two fields every
        downstream record — the withholding moves, the certificate, the ภ.ง.ด.
        report — is built from."""
        payment = self._voucher()

        wht = self._wht_lines(payment)
        self.assertEqual(len(wht), 1)
        self.assertEqual(wht.wht_tax_id, self.wht_tax)
        self.assertEqual(wht.tax_base_amount, 10000.0)
        self.assertEqual(wht.partner_id, self.payee)

    def test_rebuilding_the_entry_keeps_the_withholding(self):
        """Correcting the operation type rebuilds the entry from scratch, and
        core's rebuild flattens write-off lines into one anonymous row. Here the
        line is regenerated from the voucher's own rate and base, so there is
        nothing to lose."""
        payment = self._voucher()
        if not self.other_payment_type:
            self.skipTest("only one outbound operation type is configured")

        payment.kmitl_payment_type_id = self.other_payment_type

        wht = self._wht_lines(payment)
        self.assertEqual(len(wht), 1)
        self.assertEqual(wht.wht_tax_id, self.wht_tax)
        self.assertEqual(wht.tax_base_amount, 10000.0)
        self.assertEqual(payment.amount, 9700.0)

    # ------------------------------------------------------------------
    # Confirming
    # ------------------------------------------------------------------
    def test_confirming_refuses_a_withholding_with_no_base(self):
        payment = self._voucher()
        payment.with_context(kmitl_wht_deriving=True).wht_amount_base = 0.0

        with self.assertRaises(UserError):
            payment.action_confirm_for_bank()

    def test_confirming_refuses_a_withholding_with_no_type_of_income(self):
        payment = self._voucher(wht_cert_income_type=False)

        with self.assertRaises(UserError):
            payment.action_confirm_for_bank()

    def test_confirming_refuses_a_withholding_that_eats_the_whole_payment(self):
        """Only reachable by writing the two apart, which is what an import or a
        server action could do; the guard is there so it cannot be confirmed."""
        payment = self._voucher()
        payment.with_context(kmitl_wht_deriving=True).write({"amount": 0.0})
        payment.with_context(kmitl_wht_deriving=True).write({"wht_amount_base": 100.0})

        with self.assertRaises(UserError):
            payment.action_confirm_for_bank()

    def test_the_withholding_freezes_with_the_rest_of_the_money_side(self):
        payment = self._voucher()
        payment.action_confirm_for_bank()

        for vals in ({"wht_tax_id": False}, {"wht_amount_base": 5000.0}):
            with self.assertRaises(UserError):
                payment.write(vals)

    def test_the_type_of_income_stays_open_after_the_voucher_is_confirmed(self):
        """The one field on this form that does. It books nothing and the bank
        never saw it, and the certificate it belongs to is issued after the
        confirmation — see ADR-0008."""
        payment = self._voucher()
        payment.action_confirm_for_bank()

        payment.wht_cert_income_type = "2"

        self.assertEqual(payment.wht_cert_income_type, "2")

    # ------------------------------------------------------------------
    # The payee's certificate
    # ------------------------------------------------------------------
    def test_the_certificate_belongs_to_the_voucher_not_to_the_entry(self):
        payment = self._voucher()
        payment.action_confirm_for_bank()

        payment.action_create_wht_cert()

        cert = payment.wht_cert_ids
        self.assertEqual(len(cert), 1)
        self.assertFalse(cert.move_id)
        self.assertEqual(cert.payment_id, payment)
        self.assertEqual(cert.partner_id, self.payee)
        self.assertEqual(cert.income_tax_form, "pnd53")
        self.assertEqual(cert.name, payment.name)
        self.assertEqual(len(cert.wht_line), 1)
        self.assertEqual(cert.wht_line.base, 10000.0)
        self.assertEqual(cert.wht_line.amount, 300.0)
        self.assertEqual(cert.wht_line.wht_cert_income_type, "5")
        self.assertEqual(cert.wht_line.wht_tax_id, self.wht_tax)

    def test_the_certificate_survives_the_entry_being_posted(self):
        """Posting unlinks every certificate hanging off the entry, and the payee
        is already holding this one."""
        payment = self._voucher()
        payment.action_confirm_for_bank()
        payment.action_create_wht_cert()
        cert = payment.wht_cert_ids

        # It is not the entry's, which is the whole point: the unlink upstream
        # runs on post cannot see it.
        self.assertFalse(payment.move_id.wht_cert_ids)

        payment.move_id.wht_cert_ids.unlink()

        self.assertTrue(cert.exists())
        self.assertEqual(payment.wht_cert_ids, cert)

    def test_a_draft_voucher_has_nothing_to_certify_yet(self):
        payment = self._voucher()

        with self.assertRaises(UserError):
            payment.action_create_wht_cert()

    def test_a_voucher_withholding_nothing_certifies_nothing(self):
        payment = self._voucher(
            wht_tax_id=False, wht_amount_base=0.0, wht_cert_income_type=False
        )
        payment.amount = 9700.0
        payment.action_confirm_for_bank()

        with self.assertRaises(UserError):
            payment.action_create_wht_cert()

    def test_the_payee_is_never_left_holding_two_certificates(self):
        payment = self._voucher()
        payment.action_confirm_for_bank()
        payment.action_create_wht_cert()

        with self.assertRaises(UserError):
            payment.action_create_wht_cert()
        # Nor through the accounting office's own door on the entry.
        with self.assertRaises(UserError):
            payment.move_id.create_wht_cert()

    def test_the_entry_reports_the_certificate_the_voucher_holds(self):
        """Otherwise the banner on a posted voucher invites an accountant to
        issue a second one."""
        payment = self._voucher()
        payment.action_confirm_for_bank()
        self.assertEqual(payment.move_id.wht_cert_status, "none")

        payment.action_create_wht_cert()

        self.assertEqual(payment.move_id.wht_cert_status, "draft")

    def test_the_withholding_move_keeps_the_chosen_type_of_income(self):
        """The ภ.ง.ด. substrate is built at posting from the entry's lines, which
        know the tax but not what the officer said the income was."""
        payment = self._voucher()
        payment.wht_cert_income_type = "2"

        vals = payment.move_id._prepare_withholding_move(self._wht_lines(payment))

        self.assertEqual(vals["wht_cert_income_type"], "2")
        self.assertEqual(vals["amount_income"], 10000.0)
        self.assertEqual(vals["amount_wht"], 300.0)

    # ------------------------------------------------------------------
    # The Hand-over raises the certificates (ADR-0009)
    # ------------------------------------------------------------------
    def test_the_hand_over_raises_the_certificate_as_a_draft(self):
        payment = self._voucher()
        payment.action_confirm_for_bank()

        payment._mark_paid()

        cert = payment.wht_cert_ids
        self.assertEqual(len(cert), 1)
        self.assertEqual(cert.state, "draft")
        self.assertFalse(cert.move_id)
        self.assertEqual(cert.payment_id, payment)
        self.assertEqual(cert.wht_line.base, 10000.0)
        self.assertEqual(cert.wht_line.amount, 300.0)
        self.assertEqual(cert.wht_line.wht_cert_income_type, "5")
        self.assertEqual(cert.income_tax_form, "pnd53")

    def test_the_hand_over_raises_one_for_a_voucher_billed_through_a_request(self):
        """The kind KMITL withholds most on. It has no rate of its own — the
        withholding is on its entry — so the certificate has to be built from
        there, and the type of income comes from the rate's own default."""
        payment = self._billed_voucher()
        payment.action_confirm_for_bank()

        payment._mark_paid()

        cert = payment.wht_cert_ids
        self.assertEqual(len(cert), 1)
        self.assertEqual(cert.state, "draft")
        self.assertEqual(cert.wht_line.base, 10000.0)
        self.assertEqual(cert.wht_line.amount, 300.0)
        self.assertEqual(cert.wht_line.wht_cert_income_type, "5")

    def test_a_whole_run_is_raised_in_one_press(self):
        """Closing one e-payment file pays every payee it carried. Twenty forms
        and twenty presses is what ADR-0006 took out of this phase."""
        payments = self.Payment.browse()
        for _index in range(3):
            payments |= self._voucher()
        payments.action_confirm_for_bank()

        payments._mark_paid()

        self.assertEqual(len(payments.wht_cert_ids), 3)
        for payment in payments:
            self.assertEqual(len(payment.wht_cert_ids), 1)

    def test_a_voucher_that_already_has_one_is_left_alone(self):
        payment = self._voucher()
        payment.action_confirm_for_bank()
        payment.action_create_wht_cert()
        first = payment.wht_cert_ids

        payment._mark_paid()

        self.assertEqual(payment.wht_cert_ids, first)

    def test_a_voucher_withholding_nothing_is_given_no_certificate(self):
        payment = self._voucher(
            wht_tax_id=False, wht_amount_base=0.0, wht_cert_income_type=False
        )
        payment.amount = 9700.0
        payment.action_confirm_for_bank()

        payment._mark_paid()

        self.assertFalse(payment.wht_cert_ids)

    def test_a_certificate_that_cannot_be_written_does_not_stop_the_hand_over(self):
        """The money has reached the payee, and no document may contradict that.
        The reason goes in the chatter instead."""
        payment = self._voucher()
        payment.action_confirm_for_bank()
        # Take away every source of a type of income, which a certificate line
        # cannot exist without.
        payment.wht_cert_income_type = False
        self.wht_tax.wht_cert_income_type = False

        payment._mark_paid()

        self.assertEqual(payment.finance_state, "paid")
        self.assertFalse(payment.wht_cert_ids)
        body = payment.message_ids[:1].body or ""
        self.assertIn("certificate", body)

    # ------------------------------------------------------------------
    # The filing run
    # ------------------------------------------------------------------
    def test_a_month_is_confirmed_for_filing_in_one_press(self):
        """A certificate still in draft is invisible to the ภ.ง.ด. report, so
        this press is what puts the month in the return."""
        payments = self.Payment.browse()
        for _index in range(2):
            payments |= self._voucher()
        payments.action_confirm_for_bank()
        payments._mark_paid()
        certs = payments.wht_cert_ids
        self.assertEqual(set(certs.mapped("state")), {"draft"})

        certs.action_done()

        self.assertEqual(set(certs.mapped("state")), {"done"})

    def test_a_certificate_totals_its_lines_for_the_filing_run(self):
        payment = self._voucher()
        payment.action_confirm_for_bank()
        payment._mark_paid()

        cert = payment.wht_cert_ids

        self.assertEqual(cert.amount_base_total, 10000.0)
        self.assertEqual(cert.amount_wht_total, 300.0)

    # ------------------------------------------------------------------
    # Where the rate comes from, and where it must never appear
    # ------------------------------------------------------------------
    def test_the_payees_category_proposes_the_rate_on_the_form(self):
        payment = self.Payment.new(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
            }
        )

        payment._onchange_partner_id_wht()
        payment._onchange_wht_tax_id()

        self.assertEqual(payment.wht_tax_id, self.wht_tax)
        self.assertEqual(payment.wht_cert_income_type, "5")

    def test_an_inbound_payment_withholds_nothing(self):
        """Withholding is something a payer does. Money coming in is receipted,
        not withheld from."""
        payment = self.Payment.new(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.payee.id,
            }
        )

        payment._onchange_partner_id_wht()

        self.assertFalse(payment.wht_tax_id)

    def test_a_voucher_created_in_python_is_never_given_a_rate(self):
        """The guard against withholding a payee twice. Every voucher a
        disbursement raises is created like this, and its withholding already
        sits on the entry — an onchange cannot reach it, a compute would."""
        payment = self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
                "amount": 1000.0,
                "date": "2026-02-10",
                "journal_id": self.paying_account.journal_id.id,
                "payment_method_line_id": self.paying_account.id,
                "kmitl_payment_type_id": self.payment_type.id,
            }
        )

        self.assertFalse(payment.wht_tax_id)
        self.assertEqual(payment.amount, 1000.0)

    def test_a_voucher_billed_through_a_request_still_reads_the_entry(self):
        """Regression on the other kind of voucher: no rate of its own, the
        withholding delivered as a write-off line the way
        ``disbursement.payment.line`` delivers it."""
        payment = self._billed_voucher()

        self.assertFalse(payment.wht_tax_id)
        self.assertEqual(payment.amount_wht, 300.0)
        self.assertEqual(payment.amount_before_wht, 10000.0)
        self.assertEqual(payment.amount, 9700.0)
        self.assertEqual(self._wht_lines(payment).tax_base_amount, 10000.0)
        # And the type of income is answered from the entry, so the voucher shows
        # both halves of its withholding before the accounting office posts it.
        self.assertEqual(payment.wht_cert_income_type, "5")

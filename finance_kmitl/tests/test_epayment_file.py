# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEpaymentFile(TransactionCase):
    """The e-payment file: how vouchers get into one, and what its states claim.

    The bank localisation modules are not dependencies of this one, so ``bank`` has
    no valid selection value here and stays unset. That is deliberate — everything
    tested below is about the file's own behaviour rather than any bank's layout,
    and the derivation is asserted to hold its tongue rather than to write a value
    the database could not hold.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Export = cls.env["bank.payment.export"]
        cls.Payment = cls.env["account.payment"]

        cls.ktb_account = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )
        cls.scb_account = cls.env.ref(
            "account_kmitl.paying_account_1112210004_transfer"
        )
        cls.cheque_account = cls.env.ref(
            "account_kmitl.paying_account_1112220015_cheque"
        )
        cls.payment_type = cls.env.ref("finance_kmitl.payment_type_normal_outbound")
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        cls.payee = cls._make_payee("Payee One")
        cls.other_payee = cls._make_payee("Payee Two")

    @classmethod
    def _make_payee(cls, name):
        partner = cls.env["res.partner"].create(
            {
                "name": name,
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "partner_id": partner.id,
                "acc_number": "ACC-%s" % name.replace(" ", "-"),
                "bank_id": cls.ktb_account.bank_id.id,
            }
        )
        return partner

    # ------------------------------------------------------------------
    def _make_payment(self, paying_account=None, payee=None, amount=1000.0):
        """A voucher confirmed for the bank — the only kind a file may carry."""
        paying_account = paying_account or self.ktb_account
        payee = payee or self.payee
        payment = self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": payee.id,
                "partner_bank_id": payee.bank_ids[:1].id,
                "amount": amount,
                "date": "2026-01-15",
                "journal_id": paying_account.journal_id.id,
                "payment_method_line_id": paying_account.id,
                "kmitl_payment_type_id": self.payment_type.id,
            }
        )
        payment.action_confirm_for_bank()
        return payment

    def _make_export(self, paying_account=None, payments=None):
        paying_account = paying_account or self.ktb_account
        return self.Export.create(
            {
                "paying_account_id": paying_account.id,
                "effective_date": fields.Date.add(
                    fields.Date.context_today(self.Export), days=1
                ),
                "export_line_ids": [
                    (0, 0, {"payment_id": payment.id}) for payment in (payments or [])
                ],
            }
        )

    def _export_it(self, export):
        """Take a file as far as ออกไฟล์แล้ว without rendering any bank's layout."""
        export.action_confirm()
        export.action_done()
        return export

    def _really_export_it(self, export):
        """As the officer does it: render the file and keep it."""
        export.action_confirm()
        export.action_export_text_file()
        return export

    # ------------------------------------------------------------------
    # Pulling every payment in
    # ------------------------------------------------------------------
    def test_pulling_again_does_not_drop_the_rows_already_in_the_file(self):
        """The base searched before releasing, so the rows already in the file were
        filtered out of the result and then unlinked — a second press on a full file
        emptied it down to whatever had arrived since."""
        first, second = self._make_payment(), self._make_payment()
        export = self._make_export(payments=[first, second])
        self.assertEqual(len(export.export_line_ids), 2)

        third = self._make_payment()
        export.action_get_all_payments()

        self.assertEqual(
            export.export_line_ids.mapped("payment_id"),
            first | second | third,
            "rebuilding should have kept the two rows and added the new one",
        )

    def test_pulling_takes_only_the_matching_paying_account(self):
        ktb = self._make_payment(self.ktb_account)
        self._make_payment(self.scb_account)
        export = self._make_export(self.ktb_account)

        export.action_get_all_payments()

        self.assertEqual(export.export_line_ids.mapped("payment_id"), ktb)

    # ------------------------------------------------------------------
    # The paying account, and the bank that follows from it
    # ------------------------------------------------------------------
    def test_nothing_can_be_pulled_until_the_paying_account_is_named(self):
        """Where a missing paying account actually does damage: the picker narrows by
        it, so without one the search matches every หัวจ่าย's vouchers. Refused here
        rather than by a NOT NULL column, which would impose KMITL's rule on every
        other module's exports."""
        export = self.Export.create({})
        self._make_payment()

        with self.assertRaises(UserError):
            export.action_get_all_payments()

        self.assertFalse(export.export_line_ids)

    def test_no_bank_is_derived_for_a_bank_with_no_layout_installed(self):
        """A BIC no installed localisation has declared is not a value the
        selection can hold, so nothing is derived rather than crashing."""
        vals = self.Export._prepare_bank_vals_from_paying_account(self.ktb_account)
        known = dict(self.Export._fields["bank"]._description_selection(self.env))
        if self.ktb_account.bank_id.bic in known:
            self.assertEqual(vals["bank"], self.ktb_account.bank_id.bic)
        else:
            self.assertFalse(vals)

    def test_the_file_bank_must_be_the_bank_holding_the_paying_account(self):
        """The base constraint meant to check this compares against the payment
        journal's bank, and a KMITL journal holds none, so it never fired."""
        export = self._make_export()
        bank = self.env["res.bank"].create({"name": "Elsewhere", "bic": "ELSETHBK"})
        self.ktb_account.bank_account_id.bank_id = bank
        known = dict(self.Export._fields["bank"]._description_selection(self.env))
        if not known:
            self.skipTest("no bank localisation installed, so bank has no value to set")
        with self.assertRaises(ValidationError):
            export.bank = list(known)[0]

    # ------------------------------------------------------------------
    # Creating files from a selection of vouchers
    # ------------------------------------------------------------------
    def test_a_selection_spanning_two_paying_accounts_becomes_two_files(self):
        ktb_one = self._make_payment(self.ktb_account)
        ktb_two = self._make_payment(self.ktb_account)
        scb = self._make_payment(self.scb_account)

        action = (ktb_one | ktb_two | scb).action_create_bank_payment_export()
        wizard = self.env["bank.payment.export.create"].browse(action["res_id"])

        self.assertEqual(len(wizard.line_ids), 2)
        self.assertEqual(
            wizard.line_ids.mapped("paying_account_id"),
            self.ktb_account | self.scb_account,
        )
        ktb_line = wizard.line_ids.filtered(
            lambda line: line.paying_account_id == self.ktb_account
        )
        self.assertEqual(ktb_line.payment_count, 2)
        self.assertEqual(ktb_line.amount_total, 2000.0)

        wizard.action_create()

        self.assertEqual(
            self.Export.search_count([("paying_account_id", "=", self.ktb_account.id)]),
            1,
        )
        self.assertEqual(scb.payment_export_id.paying_account_id, self.scb_account)
        self.assertEqual(len(ktb_one.payment_export_id.export_line_ids), 2)

    def test_one_paying_account_with_nothing_pending_skips_the_wizard(self):
        payment = self._make_payment()

        action = payment.action_create_bank_payment_export()

        self.assertEqual(action["res_model"], "bank.payment.export")
        self.assertFalse(action.get("res_id"))

    def test_vouchers_can_join_a_draft_file_that_already_debits_the_account(self):
        existing = self._make_export(payments=[self._make_payment()])
        late = self._make_payment()

        action = late.action_create_bank_payment_export()
        wizard = self.env["bank.payment.export.create"].browse(action["res_id"])
        line = wizard.line_ids
        self.assertIn(existing, line.available_export_ids)

        line.destination = "existing"
        line._onchange_destination()
        self.assertEqual(line.payment_export_id, existing)

        wizard.action_create()

        self.assertEqual(late.payment_export_id, existing)
        self.assertEqual(len(existing.export_line_ids), 2)

    def test_a_second_draft_file_on_the_same_account_is_named_on_the_form(self):
        first = self._make_export(payments=[self._make_payment()])
        second = self._make_export(payments=[self._make_payment()])

        self.assertEqual(second.other_draft_export_ids, first)
        self.assertEqual(first.other_draft_export_ids, second)

        self._export_it(first)
        # The compute depends on this record's own fields, so another record leaving
        # draft does not invalidate it — the banner is right on every fresh read,
        # which is what a form load is.
        second.invalidate_recordset(["other_draft_export_ids"])
        self.assertFalse(second.other_draft_export_ids)

    # ------------------------------------------------------------------
    # What each state claims
    # ------------------------------------------------------------------
    def _attach_proof(self, export):
        export.transfer_proof_ids = self.env["ir.attachment"].create(
            {"name": "slip.pdf", "datas": base64.b64encode(b"slip")}
        )
        return export

    def test_a_result_cannot_be_recorded_before_the_file_exists(self):
        export = self._make_export(payments=[self._make_payment()])

        with self.assertRaises(UserError):
            export.action_mark_all_epayment_success()

        export.action_confirm()
        with self.assertRaises(UserError):
            export.action_confirm_epayment_success()

    def test_the_file_cannot_be_closed_without_the_banks_confirmation(self):
        """The exported file is kept on this record too, so "has an attachment"
        would be true from the moment it was produced. The proof asked for is the
        opposite document, and it has a field of its own."""
        export = self._really_export_it(
            self._make_export(payments=[self._make_payment()])
        )
        self.assertTrue(export.export_file_id, "the exported file is already attached")

        with self.assertRaises(UserError):
            export.action_confirm_epayment_success()

        self._attach_proof(export)
        action = export.action_confirm_epayment_success()
        self.assertEqual(action["res_model"], "bank.payment.export.confirm")

    def test_closing_the_file_speaks_for_every_row_including_the_bounced_one(self):
        """One press for the whole file: the payee the bank could not credit was
        settled outside the system before it, so the assertion is true of them
        too. What the press carries instead is the note saying so."""
        paid, bounced = self._make_payment(), self._make_payment()
        export = self._attach_proof(
            self._export_it(self._make_export(payments=[paid, bounced]))
        )
        bounced_line = export.export_line_ids.filtered(
            lambda line: line.payment_id == bounced
        )
        bounced_line.action_mark_epayment_failed()

        note = "PV/2026/00002 bounced — account closed. Paid in cash on 20/08."
        self.env["bank.payment.export.confirm"].create(
            {"payment_export_id": export.id, "note": note}
        ).action_confirm()

        self.assertEqual(export.state, "paid")
        self.assertEqual(export.epayment_note, note)
        self.assertEqual(
            set(export.export_line_ids.mapped("epayment_status")), {"success"}
        )
        self.assertEqual(bounced.bank_result_status, "success")
        self.assertIn(note, export.message_ids.mapped("body")[0])

    def test_closing_the_file_pays_the_vouchers_it_carries(self):
        """The press is ยืนยันจ่ายสำเร็จ for every payee in the file, so their own
        lifecycle has to say so — and, for a voucher belonging to no request,
        nothing else would tell the accounting office about it."""
        payment = self._make_payment()
        export = self._attach_proof(
            self._export_it(self._make_export(payments=[payment]))
        )
        self.assertEqual(payment.finance_state, "confirmed")

        self.env["bank.payment.export.confirm"].create(
            {"payment_export_id": export.id}
        ).action_confirm()

        self.assertEqual(payment.finance_state, "paid")
        self.assertEqual(payment, payment._hands_over_on_its_own())

    def test_closing_the_file_skips_a_voucher_already_paid(self):
        """A voucher settled by hand before the file closed is not a reason the
        file cannot close — ``_mark_paid`` refuses anything not ``confirmed``."""
        payment = self._make_payment()
        export = self._attach_proof(
            self._export_it(self._make_export(payments=[payment]))
        )
        payment.action_confirm_paid()
        self.assertEqual(payment.finance_state, "paid")

        self.env["bank.payment.export.confirm"].create(
            {"payment_export_id": export.id}
        ).action_confirm()

        self.assertEqual(export.state, "paid")

    def test_a_rejected_row_stays_rejected_when_the_file_closes(self):
        """The base keeps a row's rejection in a column that is a *related* on the
        header's state, so writing that state marks every row for recompute. Left
        alone, closing the file would take the released payee's amount back into the
        stored total and back onto the printed report."""
        kept, bounced = self._make_payment(), self._make_payment(amount=250.0)
        export = self._attach_proof(
            self._export_it(self._make_export(payments=[kept, bounced]))
        )
        total_before = export.total_amount
        export.export_line_ids.filtered(
            lambda line: line.payment_id == bounced
        ).action_reject()
        self.assertEqual(export.total_amount, total_before - 250.0)

        self.env["bank.payment.export.confirm"].create(
            {"payment_export_id": export.id}
        ).action_confirm()

        rejected = export.export_line_ids.filtered(
            lambda line: line.payment_id == bounced
        )
        self.assertEqual(rejected.state, "reject")
        self.assertEqual(export.total_amount, total_before - 250.0)
        self.assertNotEqual(bounced.finance_state, "paid")

    def test_a_closed_file_refuses_a_second_confirmation(self):
        """A dialog left open and submitted twice would replace the note, which is
        the only record of whatever the bank could not do."""
        export = self._attach_proof(
            self._export_it(self._make_export(payments=[self._make_payment()]))
        )
        Confirm = self.env["bank.payment.export.confirm"]
        Confirm.create(
            {"payment_export_id": export.id, "note": "the real note"}
        ).action_confirm()

        with self.assertRaises(UserError):
            Confirm.create(
                {"payment_export_id": export.id, "note": "clobbered"}
            ).action_confirm()

        self.assertEqual(export.epayment_note, "the real note")

    def test_the_note_is_optional(self):
        export = self._attach_proof(
            self._export_it(self._make_export(payments=[self._make_payment()]))
        )

        self.env["bank.payment.export.confirm"].create(
            {"payment_export_id": export.id}
        ).action_confirm()

        self.assertEqual(export.state, "paid")
        self.assertFalse(export.epayment_note)

    def test_only_a_confirmed_file_may_be_taken_back_to_draft(self):
        export = self._make_export(payments=[self._make_payment()])
        export.action_confirm()
        export.action_draft()
        self.assertEqual(export.state, "draft")

        self._export_it(export)
        with self.assertRaises(UserError):
            export.action_draft()

    def test_exporting_keeps_the_file_and_hands_it_out_again(self):
        export = self._make_export(payments=[self._make_payment()])
        export.action_confirm()

        action = export.action_export_text_file()

        self.assertEqual(export.state, "done")
        self.assertTrue(export.export_file_id)
        self.assertEqual(export.export_file_id.res_id, export.id)
        self.assertIn(str(export.export_file_id.id), action["url"])
        self.assertEqual(export.action_download_export_file()["url"], action["url"])
        # Not 'self': the web client redirects for that target and returns without
        # calling the button's onClose, which is what reloads the form — the record
        # would sit on screen still reading "confirmed" after the file had gone out.
        self.assertNotEqual(action.get("target"), "self")

    # ------------------------------------------------------------------
    # The payee's bank account (ADR-0003)
    # ------------------------------------------------------------------
    def test_the_payee_account_stays_correctable_until_the_file_leaves(self):
        payment = self._make_payment()
        replacement = self.env["res.partner.bank"].create(
            {
                "partner_id": self.payee.id,
                "acc_number": "ACC-CORRECTED",
                "bank_id": self.ktb_account.bank_id.id,
            }
        )
        export = self._make_export(payments=[payment])

        payment.partner_bank_id = replacement
        self.assertEqual(payment.partner_bank_id, replacement)

        self._export_it(export)
        with self.assertRaises(UserError):
            payment.partner_bank_id = self.payee.bank_ids[:1]

    def test_correcting_the_account_on_the_row_corrects_the_voucher(self):
        payment = self._make_payment()
        replacement = self.env["res.partner.bank"].create(
            {
                "partner_id": self.payee.id,
                "acc_number": "ACC-ON-THE-ROW",
                "bank_id": self.ktb_account.bank_id.id,
            }
        )
        export = self._make_export(payments=[payment])
        line = export.export_line_ids

        line.payment_partner_bank_id = replacement

        self.assertEqual(payment.partner_bank_id, replacement)
        self.assertEqual(line.payment_partner_bank_id, replacement)

    def test_the_row_follows_a_correction_made_on_the_voucher(self):
        payment = self._make_payment()
        replacement = self.env["res.partner.bank"].create(
            {
                "partner_id": self.payee.id,
                "acc_number": "ACC-ON-THE-VOUCHER",
                "bank_id": self.ktb_account.bank_id.id,
            }
        )
        line = self._make_export(payments=[payment]).export_line_ids

        payment.partner_bank_id = replacement

        self.assertEqual(line.payment_partner_bank_id, replacement)

    def test_a_cheque_keeps_its_payee_account_open_until_it_is_paid(self):
        """A cheque enters no file, so ``export_status`` never leaves draft and
        cannot be what closes the field."""
        payment = self._make_payment(self.cheque_account)
        self.assertFalse(payment.needs_bank_export)
        self.assertTrue(payment._payee_account_is_open())

        payment.finance_state = "paid"
        self.assertFalse(payment._payee_account_is_open())

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import WithholdingTaxRemittanceCommon


@tagged("post_install", "-at_install")
class TestWithholdingTaxRemittance(WithholdingTaxRemittanceCommon):
    def test_cert_starts_pending(self):
        cert = self._make_cert()
        self.assertEqual(cert.remit_state, "pending")
        self.assertEqual(cert.amount_total, 300.0)

    def test_create_remittance_from_certs(self):
        cert1 = self._make_cert(amount=300.0)
        cert2 = self._make_cert(amount=150.0)
        action = (cert1 | cert2).action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])

        self.assertEqual(remittance.state, "draft")
        self.assertEqual(remittance.income_tax_form, "pnd53")
        self.assertEqual(remittance.wht_account_id, self.wht_account_53)
        self.assertEqual(remittance.amount_total, 450.0)
        self.assertEqual(remittance.cert_ids, cert1 | cert2)
        self.assertEqual(remittance.period_month, "1")
        self.assertEqual(remittance.period_year, "2569")
        self.assertEqual(remittance.source_analytic_id, self.source_1)

    def test_create_remittance_mixed_form_raises(self):
        cert_53 = self._make_cert(income_tax_form="pnd53")
        cert_1 = self._make_cert(income_tax_form="pnd1", wht_tax=self.wht_tax_1)
        with self.assertRaises(UserError):
            (cert_53 | cert_1).action_create_remittance()

    def test_create_remittance_mixed_source_raises(self):
        cert_1 = self._make_cert(analytic_distribution=self.distribution_a)
        cert_2 = self._make_cert(analytic_distribution=self.distribution_source_2)
        with self.assertRaises(UserError):
            (cert_1 | cert_2).action_create_remittance()

    def test_create_remittance_multi_source_cert_raises(self):
        cert = self._make_cert(analytic_distribution=self.distribution_two_sources)
        with self.assertRaises(UserError):
            cert.action_create_remittance()

    def test_create_remittance_mixed_account_same_form_raises(self):
        other_account = self.env["account.account"].create(
            {
                "code": "212098",
                "name": "Another PND53 payable",
                "account_type": "liability_current",
                "wht_account": True,
                "company_id": self.company.id,
            }
        )
        other_wht_tax = self.env["account.withholding.tax"].create(
            {
                "name": "WHT 3% (53) alt",
                "account_id": other_account.id,
                "amount": 3.0,
                "income_tax_form": "pnd53",
                "company_id": self.company.id,
            }
        )
        cert1 = self._make_cert(income_tax_form="pnd53")
        cert2 = self._make_cert(income_tax_form="pnd53", wht_tax=other_wht_tax)
        with self.assertRaises(UserError):
            (cert1 | cert2).action_create_remittance()

    def test_create_remittance_not_done_raises(self):
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": self.vendor.id,
                "income_tax_form": "pnd53",
                "date": "2026-01-15",
                "wht_line": [
                    (
                        0,
                        0,
                        {
                            "wht_cert_income_type": "5",
                            "base": 1000.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "amount": 30.0,
                        },
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            cert.action_create_remittance()

    def test_action_post_creates_balanced_move_and_marks_certs(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        cert2 = self._make_cert(amount=150.0, analytic_distribution=self.distribution_b)
        action = (cert1 | cert2).action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        self._set_bank_accounts(remittance)
        remittance.partner_id = self.rd_partner

        remittance.action_post()

        self.assertEqual(remittance.state, "posted")
        self.assertNotEqual(remittance.name, "/")
        self.assertTrue(remittance.name.startswith("WHTR/"))
        self.assertEqual(remittance.move_id.state, "posted")

        move = remittance.move_id
        # 2 ใบรับรอง x 4 บรรทัด (Dr รอนำส่ง / Cr กระแสรายวัน / Dr กระแสรายวัน /
        # Cr ออมทรัพย์)
        self.assertEqual(len(move.line_ids), 8)
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

        self.assertEqual(cert1.remit_state, "remitted")
        self.assertEqual(cert2.remit_state, "remitted")

    def test_action_post_requires_bank_accounts(self):
        cert = self._make_cert()
        action = cert.action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        remittance.journal_id = self.journal_general
        with self.assertRaises(UserError):
            remittance.action_post()

        remittance.savings_account_id = self.savings_account
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_cheque_flows_from_savings_through_current_account(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance = self._set_bank_accounts(self._make_remittance(cert))

        remittance.action_post()

        lines = remittance.move_id.line_ids
        wht_lines = lines.filtered(lambda l: l.account_id == self.wht_account_53)
        current_lines = lines.filtered(lambda l: l.account_id == self.current_account)
        savings_lines = lines.filtered(lambda l: l.account_id == self.savings_account)
        self.assertEqual(sum(wht_lines.mapped("debit")), 300.0)
        # เงินเข้าและออกบัญชีกระแสรายวันเท่ากัน สุทธิเป็น 0
        self.assertEqual(sum(current_lines.mapped("debit")), 300.0)
        self.assertEqual(sum(current_lines.mapped("credit")), 300.0)
        self.assertEqual(sum(current_lines.mapped("balance")), 0.0)
        # เงินออกจริงจากบัญชีออมทรัพย์
        self.assertEqual(sum(savings_lines.mapped("credit")), 300.0)

    def test_action_cancel_reverses_move_and_restores_certs(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance = self._set_bank_accounts(self._make_remittance(cert))
        remittance.action_post()
        posted_move = remittance.move_id

        remittance.action_cancel()

        self.assertEqual(remittance.state, "cancelled")
        self.assertFalse(remittance.move_id)
        # The plain JE is reversed, not cancelled: _reverse_moves(cancel=True)
        # only reconciles reconcilable/cash lines against the reversal, it
        # never flips the original move's state.
        self.assertEqual(posted_move.state, "posted")
        reversal_move = self.env["account.move"].search(
            [("reversed_entry_id", "=", posted_move.id)]
        )
        self.assertTrue(reversal_move)
        wht_lines = (posted_move.line_ids | reversal_move.line_ids).filtered(
            lambda l: l.account_id == self.wht_account_53
        )
        self.assertEqual(sum(wht_lines.mapped("balance")), 0.0)
        self.assertFalse(cert.remittance_id)
        self.assertEqual(cert.remit_state, "pending")

    def test_remit_state_persists_across_cert_reopen(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        action = cert.action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        self._set_bank_accounts(remittance)
        remittance.action_post()
        self.assertEqual(cert.remit_state, "remitted")

        # Simulate the source document being reopened and redone: the
        # remittance link must not be an incidental side effect that a
        # base-module transition wipes out.
        cert.action_draft()
        cert.action_done()

        self.assertEqual(cert.remittance_id, remittance)
        self.assertEqual(cert.remit_state, "remitted")

    def test_action_load_pending_certs(self):
        cert1 = self._make_cert(amount=100.0)
        cert2 = self._make_cert(amount=200.0)
        remittance = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
                "source_analytic_id": self.source_1.id,
            }
        )
        remittance.action_load_pending_certs()
        self.assertEqual(remittance.cert_ids, cert1 | cert2)
        self.assertEqual(remittance.amount_total, 300.0)

    def test_load_pending_certs_filters_by_source(self):
        cert_source_1 = self._make_cert(
            amount=100.0, analytic_distribution=self.distribution_a
        )
        self._make_cert(amount=200.0, analytic_distribution=self.distribution_source_2)
        self._make_cert(
            amount=50.0, analytic_distribution=self.distribution_two_sources
        )
        self._make_cert(amount=70.0, analytic_distribution=False)
        remittance = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
                "source_analytic_id": self.source_1.id,
            }
        )
        remittance.action_load_pending_certs()
        self.assertEqual(remittance.cert_ids, cert_source_1)

    def test_cancel_records_what_it_held(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance = self._set_bank_accounts(self._make_remittance(cert))
        remittance.action_post()

        remittance.action_cancel()

        self.assertFalse(cert.remittance_id)
        self.assertFalse(remittance.cert_ids)
        last_message = remittance.message_ids.sorted(key=lambda m: m.id)[-1]
        self.assertIn(cert.name, last_message.body)

    def test_cert_on_another_draft_cannot_be_claimed(self):
        cert = self._make_cert(amount=300.0)
        action = cert.action_create_remittance()
        remittance1 = self.env["withholding.tax.remittance"].browse(action["res_id"])

        with self.assertRaises(UserError):
            cert.action_create_remittance()

        self.assertEqual(remittance1.cert_ids, cert)

    def test_copy_does_not_duplicate_certs(self):
        cert = self._make_cert(amount=300.0)
        remittance = self._make_remittance(cert)
        count_before = self.env["withholding.tax.cert"].search_count([])

        copy = remittance.copy(default={"period_month": "2"})

        self.assertEqual(
            self.env["withholding.tax.cert"].search_count([]), count_before
        )
        self.assertFalse(copy.cert_ids)

    def test_certs_without_income_tax_form_raise(self):
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": self.vendor.id,
                "date": "2026-01-15",
                "wht_line": [
                    (
                        0,
                        0,
                        {
                            "wht_cert_income_type": "5",
                            "base": 1000.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "amount": 30.0,
                        },
                    )
                ],
            }
        )
        cert.action_done()
        with self.assertRaises(UserError):
            cert.action_create_remittance()

    def test_move_has_one_line_group_per_cert(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        cert2 = self._make_cert(amount=150.0, analytic_distribution=self.distribution_b)
        remittance = self._set_bank_accounts(self._make_remittance(cert1 | cert2))

        remittance.action_post()

        move = remittance.move_id
        self.assertEqual(len(move.line_ids), 8)
        for cert in (cert1, cert2):
            cert_lines = move.line_ids.filtered(
                lambda l, cert=cert: cert.name in (l.name or "")
            )
            self.assertEqual(len(cert_lines), 4)
            wht_line = cert_lines.filtered(
                lambda l: l.account_id == self.wht_account_53
            )
            savings_line = cert_lines.filtered(
                lambda l: l.account_id == self.savings_account
            )
            self.assertEqual(wht_line.debit, cert.amount_total)
            self.assertEqual(savings_line.credit, cert.amount_total)
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def test_move_lines_carry_source_analytic(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        cert2 = self._make_cert(amount=150.0, analytic_distribution=self.distribution_b)
        remittance = self._set_bank_accounts(self._make_remittance(cert1 | cert2))

        remittance.action_post()

        move = remittance.move_id
        lines_a = move.line_ids.filtered(
            lambda l: l.analytic_distribution == self.distribution_a
        )
        lines_b = move.line_ids.filtered(
            lambda l: l.analytic_distribution == self.distribution_b
        )
        self.assertEqual(len(lines_a), 4)
        self.assertEqual(len(lines_b), 4)
        self.assertFalse(
            move.line_ids.filtered(lambda l: not l.analytic_distribution)
        )
        self.assertEqual(sum(lines_a.mapped("balance")), 0.0)
        self.assertEqual(sum(lines_b.mapped("balance")), 0.0)

    def test_post_raises_when_cert_has_no_analytic(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=False)
        remittance = self._set_bank_accounts(
            self.env["withholding.tax.remittance"].create(
                {
                    "income_tax_form": "pnd53",
                    "period_month": "1",
                    "period_year": "2569",
                    "source_analytic_id": self.source_1.id,
                }
            )
        )
        cert.remittance_id = remittance
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_post_raises_when_cert_analytic_is_incomplete(self):
        """บรรทัด WHT ต้นทางมีมิติบางบรรทัด ไม่มีบางบรรทัด → นำส่งไม่ได้"""
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_general.id,
                "date": "2026-01-15",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Vendor bill",
                            "account_id": self.expense_account.id,
                            "debit": 300.0,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT with dimensions",
                            "account_id": self.wht_account_53.id,
                            "debit": 0.0,
                            "credit": 200.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "analytic_distribution": self.distribution_a,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT without dimensions",
                            "account_id": self.wht_account_53.id,
                            "debit": 0.0,
                            "credit": 100.0,
                            "wht_tax_id": self.wht_tax_53.id,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        cert = self._make_cert(amount=300.0, source_move=move)
        remittance = self._set_bank_accounts(
            self.env["withholding.tax.remittance"].create(
                {
                    "income_tax_form": "pnd53",
                    "period_month": "1",
                    "period_year": "2569",
                    "source_analytic_id": self.source_1.id,
                }
            )
        )
        cert.remittance_id = remittance
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_duplicate_form_period_and_source_raises(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance1 = self._make_remittance(cert1)

        with self.assertRaises(ValidationError):
            self.env["withholding.tax.remittance"].create(
                {
                    "income_tax_form": "pnd53",
                    "period_month": "1",
                    "period_year": "2569",
                    "source_analytic_id": self.source_1.id,
                }
            )

        self._set_bank_accounts(remittance1)
        remittance1.action_post()
        remittance1.action_cancel()

        remittance2 = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
                "source_analytic_id": self.source_1.id,
            }
        )
        self.assertEqual(remittance2.state, "draft")

    def test_same_period_other_source_allowed(self):
        self._make_remittance(
            self._make_cert(analytic_distribution=self.distribution_a)
        )
        other = self._make_remittance(
            self._make_cert(analytic_distribution=self.distribution_source_2),
            source=self.source_2,
        )
        self.assertEqual(other.state, "draft")

    def test_cert_outside_period_raises_on_post(self):
        cert = self._make_cert(
            amount=300.0, date="2026-02-15", analytic_distribution=self.distribution_a
        )
        remittance = self._set_bank_accounts(
            self._make_remittance(cert, month="1", year="2569")
        )
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_cert_reads_only_its_own_payee_distribution(self):
        """หนึ่ง JE หักภาษีสองคู่ค้า → หนึ่งใบรับรองต่อคู่ค้า อ่านมิติของตัวเองเท่านั้น"""
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_general.id,
                "date": "2026-01-15",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Vendor bill A",
                            "account_id": self.expense_account.id,
                            "debit": 300.0,
                            "credit": 0.0,
                            "partner_id": self.vendor.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Vendor bill B",
                            "account_id": self.expense_account.id,
                            "debit": 150.0,
                            "credit": 0.0,
                            "partner_id": self.vendor_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT vendor A",
                            "account_id": self.wht_account_53.id,
                            "debit": 0.0,
                            "credit": 300.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "analytic_distribution": self.distribution_a,
                            "partner_id": self.vendor.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT vendor B",
                            "account_id": self.wht_account_53.id,
                            "debit": 0.0,
                            "credit": 150.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "analytic_distribution": self.distribution_source_2,
                            "partner_id": self.vendor_2.id,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        cert_a = self._make_cert(
            amount=300.0, partner=self.vendor, source_move=move
        )
        cert_b = self._make_cert(
            amount=150.0, partner=self.vendor_2, source_move=move
        )

        # ก่อนแก้ไข: ทั้งสองใบจะเห็นมิติของทั้งสองคู่ค้าปนกัน → นับเป็นหลายแหล่งเงิน
        # และถูกปฏิเสธเป็น multi-source ทั้งที่แต่ละใบมีแหล่งเงินเดียวจริง ๆ
        self.assertEqual(
            self.env["withholding.tax.remittance"]._cert_source_ids(cert_a),
            {self.source_1.id},
        )
        self.assertEqual(
            self.env["withholding.tax.remittance"]._cert_source_ids(cert_b),
            {self.source_2.id},
        )

        remittance_a = self._set_bank_accounts(
            self._make_remittance(cert_a, source=self.source_1)
        )
        remittance_b = self._set_bank_accounts(
            self._make_remittance(cert_b, source=self.source_2)
        )
        remittance_a.action_post()
        remittance_b.action_post()

        self.assertFalse(
            remittance_a.move_id.line_ids.filtered(
                lambda l: l.analytic_distribution != self.distribution_a
            )
        )
        self.assertFalse(
            remittance_b.move_id.line_ids.filtered(
                lambda l: l.analytic_distribution != self.distribution_source_2
            )
        )

    def test_period_year_selection_has_fixed_floor(self):
        selection = dict(
            self.env["withholding.tax.remittance"]._get_period_year_selection()
        )
        self.assertIn("2560", selection)
        self.assertNotIn("2559", selection)

    def test_create_remittance_from_old_cert_does_not_raise(self):
        # 2018-01-15 = พ.ศ. 2561: เกินหน้าต่างเลื่อน "base - 3" ของโค้ดเดิม
        # (2566 ในปีปัจจุบัน) แต่ยังอยู่เหนือพื้นล่างตายตัว 2560 ของโค้ดใหม่
        cert = self._make_cert(
            amount=300.0,
            date="2018-01-15",
            analytic_distribution=self.distribution_a,
        )
        action = cert.action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        self.assertEqual(remittance.state, "draft")
        self.assertEqual(remittance.period_year, "2561")

    def test_load_pending_certs_filters_by_period(self):
        cert_jan = self._make_cert(amount=100.0, date="2026-01-10")
        self._make_cert(amount=200.0, date="2026-02-10")
        remittance = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
                "source_analytic_id": self.source_1.id,
            }
        )
        remittance.action_load_pending_certs()
        self.assertEqual(remittance.cert_ids, cert_jan)

# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form
from odoo.tests.common import tagged

from .test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestDirectClaim(TwoApproverCommon):
    """ตั้งเบิกตรง (ADR-0005): the external memo stands in for the head's
    signature, so submit lands on ``signed`` once the memo is recorded."""

    def _draft(self, **vals):
        dr = self.DR.create(
            dict(
                {
                    "partner_type_id": self.partner.partner_type_id.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": "line",
                                "quantity": 1.0,
                                "price_unit": 100.0,
                                "partner_id": self.partner.id,
                            },
                        )
                    ],
                },
                **vals,
            )
        )
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        return dr

    def _no_exceptions(self):
        # Budget bridges add their own submit rules; this is about the memo.
        return patch.object(type(self.DR), "detect_exceptions", return_value=[])

    def test_direct_claim_needs_memo_number_and_attachment(self):
        dr = self._draft(is_direct_claim=True)
        with self._no_exceptions():
            with self.assertRaises(UserError):
                dr.action_submit()
            dr.memo_number = "อว 7201/123"
            with self.assertRaises(UserError):
                dr.action_submit()
            self.env["ir.attachment"].create(
                {
                    "name": "memo.pdf",
                    "res_model": dr._name,
                    "res_id": dr.id,
                    "raw": b"%PDF-1.4",
                }
            )
            dr.action_submit()
        self.assertEqual(dr.state, "signed")

    def test_regular_request_stops_at_submitted(self):
        dr = self._draft()
        with self._no_exceptions():
            dr.action_submit()
        self.assertEqual(dr.state, "submitted")


@tagged("post_install", "-at_install")
class TestTaxable(TwoApproverCommon):
    """มีภาษี covers VAT and WHT; a company payee type is always taxed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_type = cls.env.ref("partner_type_kmitl.partner_type_company")
        cls.person_type = cls.env.ref("partner_type_kmitl.partner_type_other")
        cls.vat = cls.env["account.tax"].create(
            {
                "name": "VAT 7% (test)",
                "amount": 7.0,
                "type_tax_use": "purchase",
            }
        )

    def test_advance_defaults_untaxed_unless_company(self):
        # Onchange behaviour only — never saved.
        form = Form(self.DR)
        form.partner_type_id = self.person_type
        self.assertTrue(form.has_tax)
        form.payment_type = "advance"
        self.assertFalse(form.has_tax)
        form.partner_type_id = self.company_type
        self.assertTrue(form.has_tax)

    def test_company_must_be_taxable(self):
        with self.assertRaises(ValidationError):
            self.DR.create({"partner_type_id": self.company_type.id, "has_tax": False})

    def test_untaxed_request_clears_line_taxes(self):
        dr = self.DR.create(
            {
                "partner_type_id": self.person_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "line",
                            "price_unit": 100.0,
                            "partner_id": self.partner.id,
                            "tax_ids": [(6, 0, self.vat.ids)],
                        },
                    )
                ],
            }
        )
        self.assertTrue(dr.line_ids.tax_ids)
        dr.has_tax = False
        self.assertFalse(dr.line_ids.tax_ids)
        self.assertFalse(dr.line_ids.wht_tax_id)
        self.assertEqual(dr.amount_tax, 0.0)


@tagged("post_install", "-at_install")
class TestPayeeBankWizard(TwoApproverCommon):
    """A requester adds a missing payee account from the draft request."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Requester",
                    "login": "pb_requester",
                    "email": "pb_requester@example.com",
                    "groups_id": [
                        (4, cls.env.ref("disbursement.group_disbursement_user").id)
                    ],
                }
            )
        )
        cls.no_bank = cls.env["res.partner"].create(
            {
                "name": "No Bank Payee",
                "partner_type_id": cls.partner.partner_type_id.id,
            }
        )
        cls.bank = cls.env["res.bank"].create({"name": "Test Bank"})

    def test_requester_adds_missing_account(self):
        dr = self.DR.with_user(self.requester).create(
            {
                "partner_type_id": self.no_bank.partner_type_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "line",
                            "price_unit": 100.0,
                            "partner_id": self.no_bank.id,
                        },
                    )
                ],
            }
        )
        self.assertFalse(dr.line_ids.partner_bank_id)
        action = dr.action_open_partner_bank_wizard()
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.requester)
            .with_context(action["context"])
            .create({})
        )
        self.assertEqual(wizard.line_ids.partner_id, self.no_bank)
        wizard.line_ids.write({"bank_id": self.bank.id, "acc_number": "9876543210"})
        wizard.action_apply()
        self.assertEqual(dr.line_ids.partner_bank_id.acc_number, "9876543210")
        self.assertEqual(self.no_bank.bank_ids, dr.line_ids.partner_bank_id)

    def test_only_on_draft(self):
        dr = self.DR.create(
            {
                "partner_type_id": self.no_bank.partner_type_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "line",
                            "price_unit": 100.0,
                            "partner_id": self.no_bank.id,
                        },
                    )
                ],
            }
        )
        dr.state = "submitted"
        with self.assertRaises(UserError):
            dr.action_open_partner_bank_wizard()

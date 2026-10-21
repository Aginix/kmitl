# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form
from odoo.tests.common import tagged

from .test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestRequestForm(TwoApproverCommon):
    """วันที่หน่วยงานลงนาม and the dimensions typed on the form."""

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
        # Budget bridges add their own submit rules; not under test here.
        return patch.object(type(self.DR), "detect_exceptions", return_value=[])

    def test_regular_request_stops_at_submitted(self):
        dr = self._draft()
        with self._no_exceptions():
            dr.action_submit()
        self.assertEqual(dr.state, "submitted")
        self.assertFalse(dr.sign_date)
        dr.action_sign()
        self.assertEqual(dr.sign_date, fields.Date.context_today(dr))
        dr.action_draft()
        self.assertFalse(dr.sign_date)

    def test_dimensions_typed_on_the_form_are_saved(self):
        """The form sends the hidden analytic_distribution with the
        dimensions: it must follow them, or saving drops what was typed."""
        fiscal_year = self.env["account.fiscal.year"].search([], limit=1) or self.env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-DIM",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
            }
        )
        form = Form(self.DR)
        form.partner_type_id = self.partner.partner_type_id
        form.account_fiscal_year_id = fiscal_year
        form.source_analytic_id = self.source
        form.department_analytic_id = self.dept
        form.fund_analytic_id = self.fund
        form.activity_analytic_id = self.activity
        dr = form.save()
        self.assertEqual(
            set(dr.analytic_distribution),
            {str(a.id) for a in (self.source, self.dept, self.fund, self.activity)},
        )
        self.assertEqual(dr.fund_analytic_id, self.fund)


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
class TestRequesterActions(TwoApproverCommon):
    """A requester resets or cancels a request up to its approval; past it
    only a finance officer cancels. Only a cancelled request is deleted."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Requester",
                "login": "ra_requester",
                "email": "ra_requester@example.com",
                "groups_id": [(4, cls.env.ref("disbursement.group_disbursement_user").id)],
            }
        )

    def test_requester_resets_and_cancels_before_approval(self):
        dr = self._make_verified_dr().with_user(self.requester)
        dr.action_draft()
        self.assertEqual(dr.state, "draft")
        dr.action_cancel()
        self.assertEqual(dr.state, "cancel")
        dr.action_draft()
        self.assertEqual(dr.state, "draft")

    def test_only_officer_cancels_an_approved_request(self):
        dr = self._make_verified_dr()
        with self._patch_final_approval():
            dr.with_user(self.finance).action_approve_finance()
            dr.with_user(self.rector).action_approve()
        self.assertEqual(dr.state, "approved")
        with self.assertRaises(UserError):
            dr.with_user(self.requester).action_cancel()
        dr.with_user(self.officer).action_cancel()
        self.assertEqual(dr.state, "cancel")

    def test_only_a_cancelled_request_is_deleted(self):
        dr = self._make_verified_dr().with_user(self.requester)
        with self.assertRaises(UserError):
            dr.unlink()
        dr.action_cancel()
        dr.unlink()
        self.assertFalse(dr.exists())

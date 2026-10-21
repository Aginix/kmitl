# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestDirectClaim(TwoApproverCommon):
    """ตั้งเบิกตรง (disbursement ADR-0005): the external memo stands in for the head's
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
            dr.sign_date = date(2026, 10, 1)
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
        # the memo's own date, not the day it was submitted
        self.assertEqual(dr.sign_date, date(2026, 10, 1))

    def test_reset_keeps_the_memo_date(self):
        dr = self._draft(
            is_direct_claim=True, memo_number="อว 7201/9", sign_date=date(2026, 10, 1)
        )
        self.env["ir.attachment"].create(
            {"name": "memo.pdf", "res_model": dr._name, "res_id": dr.id, "raw": b"%PDF"}
        )
        with self._no_exceptions():
            dr.action_submit()
        dr.action_draft()
        self.assertEqual(dr.sign_date, date(2026, 10, 1))

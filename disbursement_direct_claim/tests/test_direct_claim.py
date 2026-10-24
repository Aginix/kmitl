# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from odoo.exceptions import AccessError
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
                                "account_id": self.expense_account.id,
                                "name": "line",
                                "amount": 100.0,
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
        """Memo number, date and scan are blocking exceptions on Submit."""
        dr = self._draft(is_direct_claim=True)
        rules = {
            name: self.env.ref(
                "disbursement_direct_claim.excep_disbursement_direct_claim_" + name
            )
            for name in ("memo_number", "sign_date", "attachment")
        }
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertLessEqual(set(rules.values()), set(dr.exception_ids))
        dr.write({"memo_number": "อว 7201/123", "sign_date": date(2026, 10, 1)})
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertIn(rules["attachment"], dr.exception_ids)
        self.assertNotIn(rules["memo_number"], dr.exception_ids)
        self.assertNotIn(rules["sign_date"], dr.exception_ids)
        self.env["ir.attachment"].create(
            {
                "name": "memo.pdf",
                "res_model": dr._name,
                "res_id": dr.id,
                "raw": b"%PDF-1.4",
            }
        )
        with self._no_exceptions():
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

    def test_direct_claim_needs_the_right(self):
        users = self.env["res.users"].with_context(no_reset_password=True)
        plain = users.create(
            {
                "name": "Plain Requester",
                "login": "dc_plain",
                "email": "dc_plain@example.com",
                "groups_id": [
                    (4, self.env.ref("disbursement.group_disbursement_user").id)
                ],
            }
        )
        granted = users.create(
            {
                "name": "Direct Claim Requester",
                "login": "dc_granted",
                "email": "dc_granted@example.com",
                "groups_id": [
                    (
                        4,
                        self.env.ref(
                            "disbursement_direct_claim.group_disbursement_direct_claim"
                        ).id,
                    )
                ],
            }
        )
        with self.assertRaises(AccessError):
            self.DR.with_user(plain).create(
                {
                    "partner_type_id": self.partner.partner_type_id.id,
                    "is_direct_claim": True,
                }
            )
        with self.assertRaises(AccessError):
            self.DR.with_user(plain).with_context(default_is_direct_claim=True).create(
                {"partner_type_id": self.partner.partner_type_id.id}
            )
        dr = self._draft()
        with self.assertRaises(AccessError):
            dr.with_user(plain).is_direct_claim = True
        # Writing the value it already has is not a change.
        dr.with_user(plain).write({"is_direct_claim": False})
        # A plain user still edits a direct claim's other fields.
        dr.with_user(granted).is_direct_claim = True
        self.assertTrue(dr.is_direct_claim)
        dr.with_user(plain).memo_number = "อว 7201/7"
        self.assertEqual(dr.memo_number, "อว 7201/7")
        with self.assertRaises(AccessError):
            dr.with_user(plain).is_direct_claim = False
        # Nor may they send someone else's direct claim on.
        dr.write({"memo_number": "อว 7201/8", "sign_date": date(2026, 10, 1)})
        self.env["ir.attachment"].create(
            {"name": "memo.pdf", "res_model": dr._name, "res_id": dr.id, "raw": b"%PDF"}
        )
        with self._no_exceptions():
            with self.assertRaises(AccessError):
                dr.with_user(plain).action_submit()
            dr.with_user(granted).action_submit()
        self.assertEqual(dr.state, "signed")

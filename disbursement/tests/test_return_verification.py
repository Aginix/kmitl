# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReturnToVerification(TransactionCase):
    """Send-back: a request in the circuit goes back to its maker (draft) with a
    reason, and the maker resubmits it straight back into the circuit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env["disbursement.request"]
        AAA = cls.env["account.analytic.account"]
        dep_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_departments")
        src_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_sources")
        fund_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_funds")
        act_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_activities")
        cls.dept = AAA.create({"name": "Dept", "plan_id": dep_plan.id})
        cls.source = AAA.create({"name": "Gov", "plan_id": src_plan.id})
        cls.fund = AAA.create({"name": "Fund", "plan_id": fund_plan.id})
        cls.activity = AAA.create({"name": "Act", "plan_id": act_plan.id})
        cls.partner = cls.env["res.partner"].create({
            "name": "Vendor",
            # submit is guarded on every payee having an account
            "bank_ids": [(0, 0, {"acc_number": "1234567890"})],
        })
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.manager = users.create(
            {
                "name": "Mgr",
                "login": "rv_mgr",
                "email": "rv_mgr@example.com",
                "groups_id": [
                    (4, cls.env.ref("disbursement.group_disbursement_manager").id)
                ],
            }
        )

    def _make_signed_dr(self):
        dr = self.DR.create(
            {
                "partner_type_id": self.partner.partner_type_id.id,
                "line_ids": [
                    (0, 0, {
                        "account_id": self.expense_account.id,
                        "name": "line",
                        "amount": 100.0,
                        "partner_id": self.partner.id,
                    })
                ]
            }
        )
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        dr.action_submit()
        with self._patch_circuit_entry():
            dr.action_sign()
        self.assertIn(dr.state, ("signed", "in_progress"))
        return dr

    def _patch_circuit_entry(self):
        """A signed request stays signed whatever bridge routes it to a station."""
        return patch.object(type(self.DR), "_on_signed")

    def test_cannot_return_from_wrong_state(self):
        dr = self.DR.create(
            {
                "partner_type_id": self.partner.partner_type_id.id,
                "line_ids": [
                    (0, 0, {
                        "account_id": self.expense_account.id,
                        "name": "line",
                        "amount": 100.0,
                        "partner_id": self.partner.id,
                    })
                ]
            }
        )
        # draft -> not in the circuit, so it cannot be sent back
        with self.assertRaises(UserError):
            dr._action_return_for_edit("x")

    def test_return_for_edit_fallback_to_draft_without_source(self):
        """The generic _action_return_for_edit dispatcher falls back to the base
        signed -> draft behaviour for a DR with no correctable source."""
        dr = self._make_signed_dr()
        self.assertFalse(dr._get_return_source())
        dr._action_return_for_edit("fix it")
        self.assertEqual(dr.state, "draft")
        self.assertTrue(dr.returned_for_edit)

    def test_wizard_routes_to_send_back(self):
        dr = self._make_signed_dr()
        wizard = self.env["disbursement.return.request.wizard"].create(
            {"request_id": dr.id, "reason": "via wizard"}
        )
        wizard.action_return()
        self.assertEqual(dr.state, "draft")
        self.assertTrue(dr.returned_for_edit)
        # The maker resubmits it straight back, without a second head signature.
        with self._patch_circuit_entry():
            dr.action_resubmit_verification()
        self.assertEqual(dr.state, "signed")
        self.assertFalse(dr.returned_for_edit)

    def test_send_back_marks_the_request_until_resubmitted(self):
        dr = self._make_signed_dr()
        marker = self.env.ref("disbursement.excep_disbursement_sent_back")
        dr._action_return_for_edit("fix it")
        self.assertIn(marker, dr.exception_ids)
        self.assertEqual(dr.main_exception_id, marker)
        # Detection leaves the marker alone.
        dr.detect_exceptions()
        self.assertIn(marker, dr.exception_ids)
        with self._patch_circuit_entry():
            dr.action_resubmit_verification()
        self.assertNotIn(marker, dr.exception_ids)

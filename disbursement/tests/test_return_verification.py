# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReturnToVerification(TransactionCase):
    """Flow 2/3 return-to-verification: an approver (verified) or the accounting
    room (approved) sends the request back to the officer (signed). No budget is
    touched; the flag clears once the officer re-validates."""

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
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Svc", "type": "service"}
        )
        users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.manager = users.create(
            {
                "name": "Mgr",
                "login": "rv_mgr",
                "groups_id": [
                    (4, cls.env.ref("disbursement.group_disbursement_manager").id)
                ],
            }
        )

    def _make_signed_dr(self):
        dr = self.DR.create(
            {
                "line_ids": [
                    (0, 0, {
                        "product_id": self.product.id,
                        "name": "line",
                        "quantity": 1.0,
                        "price_unit": 100.0,
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
        dr.action_sign()
        self.assertEqual(dr.state, "signed")
        return dr

    def _make_verified_dr(self):
        dr = self._make_signed_dr()
        dr.action_validate()
        self.assertEqual(dr.state, "verified")
        return dr

    def test_return_from_verified_goes_to_signed(self):
        dr = self._make_verified_dr()
        dr._action_return_to_verification("please recheck")
        self.assertEqual(dr.state, "signed")
        self.assertTrue(dr.returned_to_verification)
        self.assertEqual(dr.return_verification_reason, "please recheck")

    def test_flag_cleared_on_revalidate(self):
        dr = self._make_verified_dr()
        dr._action_return_to_verification("recheck")
        self.assertTrue(dr.returned_to_verification)
        dr.action_validate()
        self.assertEqual(dr.state, "verified")
        self.assertFalse(dr.returned_to_verification)
        self.assertFalse(dr.return_verification_reason)

    def test_cannot_return_from_wrong_state(self):
        dr = self.DR.create(
            {
                "line_ids": [
                    (0, 0, {
                        "product_id": self.product.id,
                        "name": "line",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "partner_id": self.partner.id,
                    })
                ]
            }
        )
        # draft -> cannot return to verification
        with self.assertRaises(UserError):
            dr._action_return_to_verification("x")

    def test_return_for_edit_fallback_to_draft_without_source(self):
        """The generic _action_return_for_edit dispatcher falls back to the base
        signed -> draft behaviour for a DR with no correctable source."""
        dr = self._make_signed_dr()
        self.assertFalse(dr._get_return_source())
        dr._action_return_for_edit("fix it")
        self.assertEqual(dr.state, "draft")
        self.assertTrue(dr.returned_for_edit)

    def test_wizard_verification_mode_routes_to_return(self):
        dr = self._make_verified_dr()
        wizard = self.env["disbursement.return.request.wizard"].create(
            {"request_id": dr.id, "reason": "via wizard", "mode": "verification"}
        )
        wizard.action_return()
        self.assertEqual(dr.state, "signed")
        self.assertTrue(dr.returned_to_verification)
        self.assertEqual(dr.return_verification_reason, "via wizard")

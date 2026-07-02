# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDisbursementTierValidation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env["disbursement.request"]

        # One analytic account per required dimension so the
        # _check_analytic_distribution_complete constraint passes on submit.
        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]

        def account_for(code):
            plan = Plan.search([("code", "=", code)], limit=1)
            if not plan:
                plan = Plan.create({"name": code.title(), "code": code})
            return Account.create({"name": "Test %s" % code, "plan_id": plan.id})

        cls.analytic_distribution = {
            str(account_for(code).id): 100
            for code in ("sources", "departments", "funds", "activities")
        }

        cls.partner = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Test Service", "type": "service"}
        )

        cls.user_acct = cls._make_reviewer(
            "dtv_acct_head",
            "disbursement_tier_validation.role_disbursement_accounting_head",
        )
        cls.user_fin = cls._make_reviewer(
            "dtv_fin_director",
            "disbursement_tier_validation.role_disbursement_finance_director",
        )

    @classmethod
    def _make_reviewer(cls, login, role_xmlid):
        """Create a user whose only role is the given tier reviewer role.

        Groups are granted through base_user_role from the role, so the user
        lands in the tier's reviewer group.
        """
        role = cls.env.ref(role_xmlid)
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "role_line_ids": [(0, 0, {"role_id": role.id})],
            }
        )

    def _new_verified_dr(self):
        """Create a DR and walk it draft -> submitted -> signed -> verified.

        Reaching 'verified' auto-requests the two tier reviews.
        """
        dr = self.DR.create(
            {
                "partner_id": self.partner.id,
                "analytic_distribution": self.analytic_distribution,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        dr.action_submit()
        dr.action_sign()
        dr.action_validate()
        return dr

    def test_reviews_created_on_validate(self):
        dr = self._new_verified_dr()
        reviews = dr.review_ids.sorted("sequence")
        self.assertEqual(len(reviews), 2, "Two tier reviews must be created")
        self.assertEqual(dr.validation_status, "pending")
        # Accounting Head is reviewed first (review sequence 1), then Finance
        # Director (review sequence 2).
        self.assertEqual(reviews[0].name, "หัวหน้างานบัญชี")
        self.assertEqual(reviews[1].name, "ผู้อำนวยการกองคลัง")
        self.assertTrue(all(r.approve_sequence for r in reviews))

    def test_sequential_first_tier_only(self):
        """The second tier cannot review before the first is approved."""
        dr = self._new_verified_dr()
        reviews = dr.review_ids.sorted("sequence")
        first, second = reviews[0], reviews[1]
        self.assertTrue(first.with_user(self.user_acct).can_review)
        self.assertFalse(second.with_user(self.user_fin).can_review)

    def test_no_premature_approval(self):
        """Approving only the first tier must NOT approve the request."""
        dr = self._new_verified_dr()
        first = dr.review_ids.sorted("sequence")[0]
        dr.with_user(self.user_acct)._validate_tier(first)
        self.assertEqual(dr.state, "verified", "Must stay verified after tier 1")
        self.assertEqual(dr.validation_status, "pending")

    def test_full_approval(self):
        """Both tiers validated -> the request is approved exactly once."""
        dr = self._new_verified_dr()
        reviews = dr.review_ids.sorted("sequence")
        with patch.object(
            type(dr), "_action_approve_budget", autospec=True
        ) as mocked_budget:
            dr.with_user(self.user_acct)._validate_tier(reviews[0])
            self.assertEqual(dr.state, "verified")
            dr.with_user(self.user_fin)._validate_tier(reviews[1])
            self.assertEqual(dr.state, "approved")
        self.assertEqual(
            mocked_budget.call_count, 1, "Budget must be consumed exactly once"
        )
        self.assertEqual(dr.validation_status, "validated")

    def test_reject_returns_to_draft(self):
        dr = self._new_verified_dr()
        first = dr.review_ids.sorted("sequence")[0]
        dr.with_user(self.user_acct)._rejected_tier(first)
        self.assertEqual(dr.state, "draft", "Rejection returns the DR to draft")
        self.assertFalse(dr.review_ids, "Reviews are cleared on rejection")

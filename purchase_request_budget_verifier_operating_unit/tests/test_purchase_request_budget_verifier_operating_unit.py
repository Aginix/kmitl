from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestBudgetVerifierOperatingUnit(TransactionCase):
    """ผู้ยืนยันงบประมาณ must belong to the พ.1's own OU."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        OU = cls.env["operating.unit"]
        partner = cls.env.company.partner_id
        cls.ou_a = OU.create(
            {"name": "PR BVer OU A", "code": "PRBVA", "partner_id": partner.id}
        )
        cls.ou_b = OU.create(
            {"name": "PR BVer OU B", "code": "PRBVB", "partner_id": partner.id}
        )
        groups = (
            "purchase_request.group_purchase_request_user,"
            "purchase_request_budget.group_purchase_request_budget_commit"
        )
        cls.committer_a = cls._user("pr_bver_ou_a", groups, cls.ou_a)
        cls.committer_b = cls._user("pr_bver_ou_b", groups, cls.ou_b)
        cls.requester = cls._user(
            "pr_bver_ou_req",
            "purchase_request.group_purchase_request_user,"
            "operating_unit.group_multi_operating_unit",
            cls.ou_a | cls.ou_b,
        )

    @classmethod
    def _user(cls, login, groups, ous):
        user = new_test_user(cls.env, login=login, groups=groups)
        user.write(
            {
                "operating_unit_ids": [Command.set(ous.ids)],
                "default_operating_unit_id": ous[0].id,
            }
        )
        return user

    def _make_pr(self, ou, **vals):
        return (
            self.env["purchase.request"]
            .with_user(self.requester)
            .create(
                {
                    "title": "OU budget verifier test",
                    "requested_by": self.requester.id,
                    "operating_unit_id": ou.id,
                    **vals,
                }
            )
        )

    def test_candidates_limited_to_ou(self):
        pr = self._make_pr(self.ou_a)
        self.assertIn(self.committer_a, pr.budget_verifier_candidate_ids)
        self.assertNotIn(self.committer_b, pr.budget_verifier_candidate_ids)

    def test_cross_ou_committer_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_pr(self.ou_a, budget_verifier_id=self.committer_b.id)

    def test_onchange_ou_clears_and_autopicks(self):
        form = Form(self.env["purchase.request"].with_user(self.requester))
        form.title = "OU budget verifier test"
        form.operating_unit_id = self.ou_a
        self.assertEqual(form.budget_verifier_id, self.committer_a)
        form.operating_unit_id = self.ou_b
        self.assertEqual(form.budget_verifier_id, self.committer_b)

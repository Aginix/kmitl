# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCreateDrFromProject(TransactionCase):
    """The 'สร้างใบขอเบิก' action on kmitl.project raises a disbursement.request
    for a non-purchase expense, pre-filled from the project's reserved-budget
    context and drawing the project's shared commitment (budget ADR-0007) —
    no agx_approval in between."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")

        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-TEST",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )

        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPRJDR01",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )

    def _make_project(self, amount=100000.0):
        return self.env["kmitl.project"].create(
            {
                "name": "Test Project",
                "project_type": "project",
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_account_id": self.budget_account.id,
                "budget_amount": amount,
            }
        )

    def _approve_project(self, project):
        """Walk the approval-gated lifecycle up to the executing state a DR may be
        raised from: ยืนยัน → จองงบประมาณ → อนุมัติ (the manual fallback used when
        kmitl_project_sarabun is not installed)."""
        project.action_confirm()
        project.action_reserve_budget()
        project.action_approve()
        return project

    def test_button_hidden_until_approved(self):
        """can_create_disbursement is False in draft and while only reserved
        (to_send); it turns True once the project is approved and executing."""
        project = self._make_project()
        self.assertFalse(project.can_create_disbursement)
        project.action_confirm()
        project.action_reserve_budget()
        self.assertEqual(project.state, "to_send")
        self.assertFalse(project.can_create_disbursement)
        project.action_approve()
        self.assertTrue(project.can_create_disbursement)

    def test_action_requires_approval(self):
        """A reserved but not-yet-approved project (to_send) cannot raise a DR."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        with self.assertRaises(UserError):
            project.action_create_disbursement_request()

    def test_action_prefill_context(self):
        """The action pre-fills the DR from the project and links its shared
        commitment and full analytic distribution."""
        project = self._approve_project(self._make_project())
        commitment = project.budget_commitment_ids

        action = project.action_create_disbursement_request()
        ctx = action["context"]

        self.assertEqual(action["res_model"], "disbursement.request")
        self.assertEqual(
            ctx["default_reference"], "kmitl.project,%d" % project.id
        )
        self.assertEqual(ctx["default_budget_commitment_id"], commitment.id)
        self.assertEqual(ctx["default_budget_account_id"], self.budget_account.id)
        # The full project analytic distribution (incl. its kmitl_project
        # dimension) is prefilled so spend is attributed back to the project.
        self.assertEqual(
            ctx["default_analytic_distribution"], project.analytic_distribution
        )

    def test_create_links_project_budget(self):
        """Creating a DR that references the project wires its budget context
        server-side (_link_to_project): commitment, budget account and analytic
        distribution — regardless of the live-form prefill."""
        project = self._approve_project(self._make_project())
        commitment = project.budget_commitment_ids

        dr = self.env["disbursement.request"].create(
            {"reference": "kmitl.project,%d" % project.id}
        )

        self.assertEqual(dr.kmitl_project_id, project)
        self.assertEqual(dr.budget_commitment_id, commitment)
        self.assertEqual(dr.budget_account_id, self.budget_account)
        self.assertEqual(dr.analytic_distribution, project.analytic_distribution)
        # The DR shows up on the project's smart button.
        self.assertIn(dr, project.disbursement_request_ids)
        self.assertEqual(project.disbursement_request_count, 1)

    def test_cancel_keeps_shared_project_commitment(self):
        """Cancelling a project's disbursement request must never cancel the
        project's shared reservation — it only reverses that DR's own lines."""
        project = self._approve_project(self._make_project())
        commitment = project.budget_commitment_ids

        dr = self.env["disbursement.request"].create(
            {"reference": "kmitl.project,%d" % project.id}
        )
        self.assertEqual(dr.budget_commitment_id, commitment)

        dr.action_cancel()

        self.assertEqual(dr.state, "cancel")
        self.assertIn(commitment.state, ("reserved", "partial"))

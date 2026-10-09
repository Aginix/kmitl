# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

_DR = "disbursement.request"
_BUDGET_HOOK = "odoo.addons.disbursement.models.disbursement_request." \
    "DisbursementRequest._action_approve_budget"


@tagged("post_install", "-at_install")
class TestTwoApprover(TransactionCase):
    """A signed request walks the route verify -> Finance Division Director ->
    Rector-delegated approver; every transition goes through ``step.act``.
    The budget is obligated/consumed only when the Rector station completes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env[_DR]
        cls.Step = cls.env["disbursement.step"]
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
        cls.finance = users.create({
            "name": "Finance Director",
            "login": "ta_finance",
            "groups_id": [
                (4, cls.env.ref(
                    "disbursement_wst_approve_finance."
                    "group_disbursement_finance_director").id)
            ],
        })
        cls.rector = users.create({
            "name": "Rector Delegate",
            "login": "ta_rector",
            "groups_id": [
                (4, cls.env.ref(
                    "disbursement_wst_approve_rector."
                    "group_disbursement_rector_delegate").id)
            ],
        })
        cls.officer = users.create({
            "name": "Officer",
            "login": "ta_officer",
            "groups_id": [
                (4, cls.env.ref("disbursement.group_disbursement_officer").id)
            ],
        })
        cls.act_finance = cls.env.ref(
            "disbursement_wst_approve_finance.mail_activity_dr_approve_finance")
        cls.act_rector = cls.env.ref(
            "disbursement_wst_approve_rector.mail_activity_dr_approve_rector")
        # These tests walk the three request-phase stations end to end, so the
        # route must hold exactly those: any further station module installed
        # alongside (billing, payment, ...) appends its own line to the same
        # standard route and would leave the request short of ``done``.
        cls.env.ref("disbursement_wst.route_default").line_ids.filtered(
            lambda line: line.station_id.code
            not in ("verify", "approve_finance", "approve_rector")
        ).unlink()

    def _todos(self, dr, act_type):
        return dr.activity_ids.filtered(lambda a: a.activity_type_id == act_type)

    def _act(self, dr, user, note=None):
        """Act on the request's current step as ``user``."""
        return dr.current_step_id.with_user(user).act(note)

    def _steps(self, dr):
        return self.Step.search([("request_id", "=", dr.id)])

    def _make_signed_dr(self):
        dr = self.DR.create({
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "name": "line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "partner_id": self.partner.id,
            })],
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        dr.action_submit()
        dr.action_sign()
        self.assertEqual(dr.state, "in_progress")
        self.assertEqual(dr.station_code, "verify")
        return dr

    def _make_verified_dr(self):
        dr = self._make_signed_dr()
        self._act(dr, self.officer)
        self.assertEqual(dr.station_code, "approve_finance")
        return dr

    def test_verify_opens_finance_station_with_todo(self):
        dr = self._make_verified_dr()
        # The core state stays in_progress; the station is the sub-status.
        self.assertEqual(dr.state, "in_progress")
        # A Todo was pushed to the Finance Director group. The fan-out reaches
        # every member, and security.xml seats root/admin in the group too, so
        # assert membership rather than a single assignee.
        finance_todos = self._todos(dr, self.act_finance)
        self.assertIn(self.finance, finance_todos.user_id)
        self.assertFalse(self._todos(dr, self.act_rector))

    def test_full_route_to_done(self):
        dr = self._make_verified_dr()
        with patch(_BUDGET_HOOK) as budget_hook:
            # Station 2: Finance Director — no budget touched, hands to the
            # Rector delegate.
            self._act(dr, self.finance)
            budget_hook.assert_not_called()
            self.assertEqual(dr.station_code, "approve_rector")
            self.assertEqual(dr.state, "in_progress")
            self.assertEqual(dr.budget_consumed_amount, 0.0)
            self.assertFalse(self._todos(dr, self.act_finance))
            self.assertIn(self.rector, self._todos(dr, self.act_rector).user_id)

            # Station 3: Rector-delegated approver — the budget cut fires here
            # only, and the last station completing finishes the request.
            self._act(dr, self.rector)
            budget_hook.assert_called_once()
        self.assertEqual(dr.state, "done")
        self.assertFalse(dr.current_step_id)
        self.assertFalse(self._todos(dr, self.act_rector))
        steps = self._steps(dr).sorted("sequence")
        self.assertEqual(
            steps.mapped("station_code"),
            ["verify", "approve_finance", "approve_rector"],
        )
        self.assertEqual(steps.mapped("state"), ["done"] * 3)
        self.assertEqual(
            [step.acted_by_id for step in steps],
            [self.officer, self.finance, self.rector],
        )

    def test_budget_attempted_only_at_rector_station(self):
        """Finance approval must not touch the budget; the Rector step does."""
        dr = self._make_verified_dr()
        self._act(dr, self.finance)
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        # No commitment linked → the Rector station reaches the budget guard.
        with self.assertRaises(UserError):
            self._act(dr, self.rector)

    def test_only_the_station_group_may_act(self):
        dr = self._make_signed_dr()
        # At verification neither approver is authorised.
        with self.assertRaises(AccessError):
            self._act(dr, self.rector)
        with self.assertRaises(AccessError):
            self._act(dr, self.finance)
        self._act(dr, self.officer)
        # At the finance station neither the officer nor the Rector delegate
        # may skip ahead.
        with self.assertRaises(AccessError):
            self._act(dr, self.officer)
        with self.assertRaises(AccessError):
            self._act(dr, self.rector)
        self.assertEqual(dr.station_code, "approve_finance")

    def test_cancel_clears_the_route(self):
        dr = self._make_verified_dr()
        dr.action_cancel()
        self.assertEqual(dr.state, "cancel")
        self.assertFalse(dr.route_id)
        self.assertFalse(self._steps(dr))
        self.assertFalse(self._todos(dr, self.act_finance))

    # ------------------------------------------------------------------
    # Divert: something is wrong, name the station that must look at it
    # ------------------------------------------------------------------
    def _divert(self, dr, user, station_code, come_back=True, note="wrong"):
        station = self.env["disbursement.station"].search(
            [("code", "=", station_code)]
        )
        return dr.current_step_id.with_user(user).divert(station, come_back, note)

    def test_divert_and_come_back(self):
        """X -> Y -> X -> (route continues): the diverting station is queued
        again behind the detour."""
        dr = self._make_verified_dr()
        self._divert(dr, self.finance, "verify")
        self.assertEqual(dr.station_code, "verify")
        self._act(dr, self.officer)
        self.assertEqual(dr.station_code, "approve_finance")
        self._act(dr, self.finance)
        self.assertEqual(dr.station_code, "approve_rector")
        steps = self._steps(dr).sorted(lambda s: (s.sequence, s.id))
        self.assertEqual(
            steps.mapped("station_code"),
            ["verify", "approve_finance", "verify", "approve_finance", "approve_rector"],
        )
        self.assertEqual(
            steps.mapped("origin"),
            ["route", "route", "insert", "resume", "route"],
        )
        self.assertEqual(
            steps.mapped("disposition"),
            ["forward", "divert", "forward", "forward", False],
        )
        self.assertEqual(
            len(set(steps.mapped("sequence"))), len(steps), "slots never tie"
        )
        self.assertEqual(steps[2].inserted_by_step_id, steps[1])
        self.assertEqual(steps[3].inserted_by_step_id, steps[1])

    def test_divert_without_coming_back(self):
        """X -> Y -> (route continues): the request does not return to X."""
        dr = self._make_verified_dr()
        self._divert(dr, self.finance, "verify", come_back=False)
        self._act(dr, self.officer)
        self.assertEqual(dr.station_code, "approve_rector")
        steps = self._steps(dr).sorted(lambda s: (s.sequence, s.id))
        self.assertEqual(
            steps.mapped("station_code"),
            ["verify", "approve_finance", "verify", "approve_rector"],
        )

    def test_divert_needs_a_reason_and_the_group(self):
        dr = self._make_verified_dr()
        with self.assertRaises(UserError):
            self._divert(dr, self.finance, "verify", note=False)
        with self.assertRaises(AccessError):
            self._divert(dr, self.officer, "verify")
        with self.assertRaises(UserError):
            self._divert(dr, self.finance, "approve_finance")
        self.assertEqual(dr.station_code, "approve_finance")

    def test_divert_target_must_have_its_prerequisites_done(self):
        """Diverting into a station that has to come after one the request has
        not finished is refused, as it would be by the route."""
        dr = self._make_signed_dr()
        with self.assertRaises(UserError):
            self._divert(dr, self.officer, "approve_rector")
        self.assertEqual(dr.station_code, "verify")

    def test_a_detour_prints_one_signature_cell_per_station(self):
        dr = self._make_verified_dr()
        self._divert(dr, self.finance, "verify")
        self._act(dr, self.officer)
        self._act(dr, self.finance)
        cells = dr.signature_step_ids
        self.assertEqual(cells.mapped("station_code"), ["verify", "approve_finance"])
        # The latest visit of each, not the first.
        self.assertEqual(cells[0].origin, "insert")
        self.assertEqual(cells[1].origin, "resume")

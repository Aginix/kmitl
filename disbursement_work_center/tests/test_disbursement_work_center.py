# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon

STATIONS = ("check", "director", "rector", "bill", "audit", "authorize")


@tagged("post_install", "-at_install")
class TestDisbursementWorkCenter(TwoApproverCommon):
    """The DR on the seeded stations: signing enters the circuit, forwarding
    out of the last station completes it, and the station decides who may
    edit, send back or cancel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["work.center.act"]._reflect_acts()
        cls.stations = {
            key: env.ref("disbursement_work_center.station_" + key) for key in STATIONS
        }
        cls.outsider = (
            env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Outsider Officer",
                    "login": "work_center_outsider",
                    "email": "work_center_outsider@example.com",
                    "groups_id": [
                        (4, env.ref("disbursement.group_disbursement_officer").id)
                    ],
                }
            )
        )
        # The seeded stations start empty: seat one member each, and let the
        # first station open the lines for editing.
        members = {
            "check": cls.officer,
            "director": cls.finance,
            "rector": cls.rector,
            "bill": cls.officer,
            "audit": cls.officer,
            "authorize": cls.finance,
        }
        cls.members = members
        for key, station in cls.stations.items():
            station.member_ids = [(6, 0, members[key].ids)]
        cls.stations["check"].allowed_edit_ids = env["work.center.act"].search(
            [("code", "=", "disbursement.edit_lines")]
        )

    def _signed_dr(self):
        """Signed for real: unlike ``_make_signed_dr`` it enters the circuit."""
        dr = self.DR.create(
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
            }
        )
        dr.analytic_distribution = {
            str(a.id): 100 for a in (self.dept, self.source, self.fund, self.activity)
        }
        dr.action_submit()
        dr.action_sign()
        return dr

    def _forward(self, dr):
        station = dr.work_center_id
        key = next(k for k, v in self.stations.items() if v == station)
        dr.with_user(self.members[key]).action_work_center_forward()

    def _arrival_todos(self, dr):
        arrival = self.env.ref("work_center.mail_activity_station_arrival")
        return dr.activity_ids.filtered(lambda a: a.activity_type_id == arrival)

    def test_signing_enters_the_first_station(self):
        dr = self._signed_dr()
        self.assertEqual(dr.state, "in_progress")
        self.assertEqual(dr.work_center_id, self.stations["check"])
        visit = dr.work_center_open_visit_id
        self.assertEqual(visit.arrival_act, "enter")
        self.assertEqual(visit.responsible_user_ids, self.officer)
        self.assertEqual(self._arrival_todos(dr).user_id, self.officer)

    def test_forwarding_walks_the_route_and_the_last_exit_is_done(self):
        dr = self._signed_dr()
        self._forward(dr)
        self.assertEqual(dr.work_center_id, self.stations["director"])
        first = dr.work_center_visit_ids.filtered(
            lambda v: v.work_center_id == self.stations["check"]
        )
        self.assertEqual(first.departure_act, "forward")
        for _i in range(5):
            self._forward(dr)
        self.assertEqual(dr.state, "done")
        self.assertFalse(dr.work_center_id)
        self.assertEqual(dr.settlement_stage, "none")
        self.assertEqual(dr._work_center_last_visit().departure_act, "exit")
        self.assertFalse(self._arrival_todos(dr))

    def test_send_back_leaves_and_resubmit_reenters_at_the_first_station(self):
        dr = self._signed_dr()
        self._forward(dr)
        wizard = (
            self.env["disbursement.return.request.wizard"]
            .with_user(self.finance)
            .create({"request_id": dr.id, "reason": "fix the lines"})
        )
        wizard.action_return()
        self.assertEqual(dr.state, "draft")
        self.assertFalse(dr.work_center_id)
        visit = dr.work_center_visit_ids.filtered(
            lambda v: v.departure_act == "send_back"
        )
        self.assertEqual(visit.departure_reason, "fix the lines")
        dr.action_resubmit_verification()
        self.assertEqual(dr.state, "in_progress")
        self.assertEqual(dr.work_center_id, self.stations["check"])
        self.assertEqual(dr.work_center_open_visit_id.arrival_act, "resubmit")

    def test_only_the_holding_station_may_take_a_request_out(self):
        dr = self._signed_dr()
        self.env.invalidate_all()
        outsider = dr.with_user(self.outsider)
        with self.assertRaises(AccessError):
            outsider.action_draft()
        with self.assertRaises(AccessError):
            outsider.action_cancel()
        with self.assertRaises(AccessError):
            outsider._action_return_for_edit("no")
        self.assertEqual(dr.state, "in_progress")
        dr.with_user(self.officer).action_cancel()
        self.assertEqual(dr.state, "cancel")
        self.assertFalse(dr.work_center_id)

    def test_verification_officer_is_the_assignee_of_the_station(self):
        self.env["work.center.assignment.rule"].create(
            {
                "work_center_id": self.stations["check"].id,
                "model_id": self.env["ir.model"]._get_id("disbursement.request"),
                "user_id": self.members["check"].id,
            }
        )
        dr = self._signed_dr()
        self.assertEqual(dr.work_center_assignee_id, self.members["check"])
        self.assertEqual(dr._verification_officer(), self.members["check"])

    def test_the_station_decides_what_can_be_edited(self):
        dr = self._signed_dr()
        self.env.invalidate_all()
        self.assertTrue(dr.with_user(self.officer).can_edit_lines)
        self.assertFalse(dr.with_user(self.officer).can_edit_header)
        self._forward(dr)
        self.env.invalidate_all()
        self.assertFalse(dr.with_user(self.finance).can_edit_lines)

    def test_act_names_follow_the_language(self):
        act = self.env["work.center.act"].search(
            [("code", "=", "disbursement.validate")]
        )
        if not act:
            self.skipTest("disbursement_validation is not installed")
        if "th_TH" not in dict(self.env["res.lang"].get_installed()):
            self.skipTest("th_TH is not installed")
        self.assertEqual(act.with_context(lang="th_TH").name, "ตรวจสอบ")

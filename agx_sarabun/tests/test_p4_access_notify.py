# -*- coding: utf-8 -*-
"""P4 — access record-rules + mail.activity notifications."""
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP4Access(SarabunCommon):
    def _can_read(self, doc, user):
        return bool(self.Doc.with_user(user).search([("id", "=", doc.id)]))

    def test_sender_can_read(self):
        """The author sees their own หนังสือ."""
        doc = self._make_doc(sender=self.user_a)
        self.assertTrue(self._can_read(doc, self.user_a))

    def test_non_actor_cannot_read(self):
        """A user with no relation to the document cannot see it."""
        doc = self._make_doc(sender=self.user_a)
        self.assertFalse(self._can_read(doc, self.user_b))

    def test_waiting_step_grants_no_visibility(self):
        """A pre-seeded but still-waiting step grants NO read."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        # not sent yet → step is waiting
        self.assertFalse(self._can_read(doc, self.user_b))

    def test_active_step_actor_can_read(self):
        """An actor of an active step can read — keyed off the snapshot holders."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self.assertTrue(self._can_read(doc, self.user_b))

    def test_position_actor_no_personal_target_can_read(self):
        """Position-targeted actor (holder) can read once active — the old hide bug fix.

        Visibility keys off the per-person sarabun.step.recipient rows created at
        activation, so a Position/Unit target resolves to readable users.
        """
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="position",
                       position=self.pos)  # holder = user_a
        doc.action_send()
        self.assertTrue(self._can_read(doc, self.user_a))

    def test_manager_sees_all(self):
        """Managers retain see-all in v1."""
        doc = self._make_doc(sender=self.user_a)
        self.assertTrue(self._can_read(doc, self.manager))

    # ----------------------------------------------------------- notifications
    def _activities(self, doc, user):
        return self.env["mail.activity"].search([
            ("res_model", "=", "sarabun.document"),
            ("res_id", "=", doc.id),
            ("user_id", "=", user.id),
        ])

    def test_activity_per_holder_and_first_to_act_autoclear(self):
        """Each holder of an active gating step gets an activity; first-to-act clears the rest."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", target_mode="position",
                       position=self.pos_multi)  # holders a + b
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertTrue(self._activities(doc, self.user_a))
        self.assertTrue(self._activities(doc, self.user_b))

        step10 = doc.routing_step_ids.filtered(lambda s: s.order == 10)
        self._act(step10, "complete", self.user_a)  # first-to-act
        # the other holder's pending activity is auto-cleared
        self.assertFalse(self._activities(doc, self.user_b))

    def test_acknowledge_step_schedules_ack_activity(self):
        """Every active step now raises an activity (ADR-0014) — gating AND a pure
        รับทราบ / CC alike — picking the type by discriminator (gating OR
        show_signature): a gating step → EXECUTION (_action), a read-only รับทราบ →
        ACKNOWLEDGEMENT (_ack)."""
        action_type = self.env.ref("agx_sarabun.mail_activity_sarabun_action")
        ack_type = self.env.ref("agx_sarabun.mail_activity_sarabun_ack")
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.user_b)  # non-gating รับทราบ
        doc.action_send()
        acts_a = self._activities(doc, self.user_a)
        acts_b = self._activities(doc, self.user_b)
        self.assertTrue(acts_a)
        self.assertTrue(acts_b, "รับทราบ now raises an activity too (ADR-0014)")
        self.assertEqual(acts_a.activity_type_id, action_type)  # gating → execution
        self.assertEqual(acts_b.activity_type_id, ack_type)     # รับทราบ → acknowledgement

    def test_acknowledge_sign_step_schedules_execution_activity(self):
        """รับทราบและลงนาม is non-gating yet SIGNS the letter (show_signature), so its
        activity is EXECUTION (_action) — a signature can't be Mark-as-Read'd away
        (discriminator = gating OR show_signature)."""
        action_type = self.env.ref("agx_sarabun.mail_activity_sarabun_action")
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)  # gating
        self._add_step(doc, order=10, verb="acknowledge_sign", target_mode="person",
                       user=self.user_b)  # non-gating but show_signature
        doc.action_send()
        acts_b = self._activities(doc, self.user_b)
        self.assertTrue(acts_b)
        self.assertEqual(acts_b.activity_type_id, action_type)

    # -------------------------------------------- acting as a non-sender actor (ACL)
    def test_non_sender_actor_can_complete(self):
        """A non-sender approver completes their step with NO document-write rights —
        the lifecycle transition runs privileged, gated by the authority check. Acts
        as user_b via with_user (the doc's sender is the setUpClass admin)."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        step = self._active_step(doc)
        with self.mute_pdf():
            step.with_user(self.user_b).act_on_step("complete", actor=self.user_b)
        self.assertTrue(doc.is_completed)
        # stays readable in the actor's incoming box after the route finishes
        self.assertTrue(self._can_read(doc, self.user_b))

    def test_non_sender_actor_can_reject(self):
        """A non-sender approver can reject (writes state='rejected') without doc-write."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        step = self._active_step(doc)
        step.with_user(self.user_b).act_on_step(
            "reject", {"note": "ไม่อนุมัติ"}, actor=self.user_b
        )
        self.assertEqual(doc.state, "rejected")
        self.assertTrue(self._can_read(doc, self.user_b))  # reached → still readable

    def test_reached_unacted_holder_keeps_read_after_reject(self):
        """A holder reached (recipient row) but not yet acted keeps read access after
        another actor rejects — their step becomes 'skipped', but the recipient row
        (which visibility now keys on) persists."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.user_b)  # non-gating; reached, will not act
        doc.action_send()
        self.assertTrue(self._can_read(doc, self.user_b))  # reached
        step_a = doc.routing_step_ids.filtered(
            lambda s: s.verb == self._verb("sign_approve")
        )
        step_a.with_user(self.user_a).act_on_step(
            "reject", {"note": "no"}, actor=self.user_a
        )
        self.assertEqual(doc.state, "rejected")
        # user_b's ack step is now skipped, but their recipient row persists → readable
        self.assertTrue(self._can_read(doc, self.user_b))

    # === Origin-independent visibility: a หนังสือ recipient sees the letter and its
    #     report/preview even with NO rights on the origin record (the หนังสือ's ACL
    #     governs, not the origin's). ===
    def test_recipient_reads_origin_reference_without_origin_rights(self):
        """A Route recipient may open the หนังสือ — and see the origin's name shown on
        it — even though they cannot read the origin record itself. The reference
        resolves under sudo, so opening the form does not trip the origin's ACL."""
        origin = self.Origin.create(
            {"name": "PR-เฉพาะแอดมิน", "test_department_id": self.dept.id}
        )
        doc = self._make_doc(sender=self.user_a, origin=origin)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()  # user_b becomes a recipient → may read the หนังสือ
        # user_b genuinely cannot read the origin model …
        with self.assertRaises(AccessError):
            self.Origin.with_user(self.user_b).browse(origin.id).read(["name"])
        # … yet the origin reference on the หนังสือ still resolves for them.
        self.assertEqual(
            doc.with_user(self.user_b).origin_reference, origin.display_name
        )

    def test_recipient_resolves_delegated_report_under_sudo(self):
        """The official document's delegated (origin) report resolves under sudo, so a
        recipient without origin rights still gets it — and an origin override that
        reads its own fields in _get_sarabun_report_action never trips their ACL."""
        origin = self.Origin.create(
            {"name": "PR-รายงาน", "test_department_id": self.dept.id}
        )
        doc = self._make_doc(sender=self.user_a, origin=origin)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        seen = {}
        report = self.env.ref("agx_sarabun.action_report_sarabun_document")

        def fake_report_action(origin_self):
            seen["su"] = origin_self.env.su
            return report

        with patch.object(
            type(self.Origin), "_get_sarabun_report_action", fake_report_action
        ):
            action = doc.with_user(self.user_b)._get_delegated_report_action()
        self.assertEqual(action, report)
        self.assertTrue(
            seen.get("su"), "origin report must resolve under sudo, not the user's ACL"
        )

    # === Acting as the actual actor (with_user) — the whole engine must run under
    #     the acting user's ACL, not admin, so the authority-check-then-sudo path is
    #     exercised end to end (ADR-0013). ===
    def test_plain_user_send_schedules_activities(self):
        """A plain sarabun user (not admin) sends their own หนังสือ: send runs under
        their ACL, mints recipient rows + native activities for the holders, and the
        holder becomes readable — the send path is no longer masked by an admin env."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.user_a)  # a รับทราบ CC too
        doc.with_user(self.user_a).action_send()
        self.assertEqual(doc.state, "circulating")
        self.assertTrue(self._activities(doc, self.user_b))   # execution
        self.assertTrue(self._activities(doc, self.user_a))   # acknowledgement
        self.assertTrue(self._can_read(doc, self.user_b))

    def test_direct_by_actor_schedules_next_holder_activity(self):
        """เกษียนสั่งการ (Direct) by the active actor inserts the next step and the new
        holder gets an activity — driven with_user(actor), no admin env."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.with_user(self.user_a).action_send()
        step = self._active_step(doc)
        step.with_user(self.user_b).act_on_step(
            "direct", {"note": "ส่งต่อ", "verb": self._verb("acknowledge").id,
                       "target_mode": "person", "employee_id": self.emp_a.id},
            actor=self.user_b,
        )
        # user_a is the new holder of the inserted step → has an activity + can read
        self.assertTrue(self._activities(doc, self.user_a))
        self.assertTrue(self._can_read(doc, self.user_a))

    def test_delegate_by_actor_moves_activity_to_new_holder(self):
        """มอบหมาย (Delegate) reassigns THIS step: the original holder's to-do is
        cleared and the new holder gets a fresh one — driven with_user(actor)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.with_user(self.user_a).action_send()
        step = self._active_step(doc)
        self.assertTrue(self._activities(doc, self.user_b))
        step.with_user(self.user_b).act_on_step(
            "delegate", {"target_mode": "person", "employee_id": self.emp_a.id},
            actor=self.user_b,
        )
        self.assertFalse(self._activities(doc, self.user_b), "original to-do cleared")
        self.assertTrue(self._activities(doc, self.user_a), "new holder to-do")
        self.assertTrue(self._can_read(doc, self.user_a))

    # === Archive-path visibility (ADR-0013): read persists across the transitions
    #     that archive the whole chain (active=False) — ตีกลับ / ดึงกลับ. reached_user_ids
    #     spans archived attempts, so a prior actor never loses the audit trail. ===
    def test_read_persists_after_return(self):
        """ตีกลับ (Return) archives the chain; the returner (and a reached CC) keep read."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.manager)  # reached CC, will not act
        doc.with_user(self.user_a).action_send()
        self.assertTrue(self._can_read(doc, self.user_b))
        step = doc.routing_step_ids.filtered(
            lambda s: s.verb == self._verb("sign_approve") and s.state == "active"
        )
        step.with_user(self.user_b).act_on_step(
            "return", {"note": "แก้ไข", "destination": "sender_restart"},
            actor=self.user_b,
        )
        self.assertEqual(doc.state, "returned")
        # the chain is archived — routing_step_ids re-seeded fresh — yet the prior
        # attempt's holders stay readable via reached_user_ids
        self.assertTrue(doc.archived_step_ids)
        self.assertTrue(self._can_read(doc, self.user_b))

    def test_read_persists_after_pull_back(self):
        """ดึงกลับ (Recall) by the sender archives the chain; a holder reached in the
        pulled-back attempt keeps read."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.with_user(self.user_a).action_send()
        self.assertTrue(self._can_read(doc, self.user_b))
        doc.with_user(self.user_a).action_pull_back(reason="ขอแก้")
        self.assertEqual(doc.state, "returned")
        self.assertTrue(doc.archived_step_ids)
        self.assertTrue(self._can_read(doc, self.user_b))  # reached in prior attempt

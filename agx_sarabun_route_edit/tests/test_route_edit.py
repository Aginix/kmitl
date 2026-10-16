"""Admin route edit on a circulating หนังสือ (ADR-0018).

Reuses agx_sarabun's SarabunCommon fixtures; adds a route-editor user. Edits go
through the document's o2m commands, like a form save, as the editor.
"""

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import new_test_user, tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestSarabunRouteEdit(SarabunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.editor = new_test_user(
            cls.env,
            login="sb_route_editor",
            name="ผู้แก้เส้นทาง",
            groups="base.group_user,agx_sarabun_route_edit.group_sarabun_route_edit",
        )
        cls.env["hr.employee"].create({"name": "ผู้แก้เส้นทาง", "user_id": cls.editor.id})
        cls.user_c = new_test_user(
            cls.env,
            login="sb_user_c",
            name="ผู้ใช้ ค",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        cls.emp_c = cls.env["hr.employee"].create(
            {"name": "ผู้ใช้ ค", "user_id": cls.user_c.id}
        )

    # ------------------------------------------------------------------ helpers
    def _circulating_doc(self):
        """Sender user_a; stage 10 = endorse by user_b (active after send),
        stage 20 = sign_approve (issues the number) by user_a (waiting)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertEqual(doc.state, "circulating")
        return doc

    def _step(self, doc, order):
        return doc.routing_step_ids.filtered(lambda s: s.order == order)

    def _edit(self, doc, commands, user=None):
        doc.with_user(user or self.editor).write({"routing_step_ids": commands})

    def _activity_users(self, step):
        return (
            self.env["sarabun.routing.step.activity"]
            .sudo()
            .search([("step_id", "=", step.id)])
            .mapped("user_id")
        )

    def _assert_no_access(self, doc, user):
        """``user`` was taken off the Route: no reach, no read, not a follower."""
        self.assertNotIn(user, doc.reached_user_ids)
        self.assertNotIn(user.partner_id, doc.message_partner_ids)
        with self.assertRaises(AccessError):
            doc.with_user(user).check_access_rule("read")

    # ------------------------------------------------------------------ tests
    def test_retarget_waiting_step(self):
        doc = self._circulating_doc()
        waiting = self._step(doc, 20)
        self._edit(doc, [Command.update(waiting.id, {"employee_id": self.emp_c.id})])
        self.assertEqual(waiting.state, "waiting")
        self._act(self._step(doc, 10), "complete", self.user_b)
        self.assertEqual(waiting.state, "active")
        self.assertEqual(waiting.actor_user_ids, self.user_c)

    def test_retarget_active_step_moves_todo(self):
        doc = self._circulating_doc()
        active = self._step(doc, 10)
        self.assertEqual(self._activity_users(active), self.user_b)
        self.assertIn(self.user_b, doc.reached_user_ids)
        self.assertIn(self.user_b.partner_id, doc.message_partner_ids)
        self._edit(doc, [Command.update(active.id, {"employee_id": self.emp_c.id})])
        self.assertEqual(active.state, "active")
        self.assertEqual(active.actor_user_ids, self.user_c)
        self.assertEqual(self._activity_users(active), self.user_c)
        self.assertEqual(active.recipient_ids.user_id, self.user_c)
        # The person taken off the step loses access to the หนังสือ.
        self._assert_no_access(doc, self.user_b)
        self.assertIn(self.user_c, doc.reached_user_ids)
        self._act(active, "complete", self.user_c)
        self.assertEqual(active.state, "done")

    def test_active_step_only_target_editable(self):
        doc = self._circulating_doc()
        active = self._step(doc, 10)
        with self.assertRaises(UserError):
            self._edit(
                doc, [Command.update(active.id, {"verb": self._verb("acknowledge").id})]
            )

    def test_add_step_in_current_stage_activates(self):
        doc = self._circulating_doc()
        self._edit(
            doc,
            [
                Command.create(
                    {
                        "order": 10,
                        "verb": self._verb("endorse").id,
                        "target_mode": "person",
                        "employee_id": self.emp_c.id,
                    }
                )
            ],
        )
        added = self._step(doc, 10).filtered(lambda s: s.employee_id == self.emp_c)
        self.assertEqual(added.state, "active")
        self.assertEqual(added.created_by_disposition, "direct")
        self.assertEqual(added.actor_user_ids, self.user_c)

    def test_add_step_before_frontier_raises(self):
        doc = self._circulating_doc()
        self._act(self._step(doc, 10), "complete", self.user_b)
        with self.assertRaises(UserError):
            self._edit(
                doc,
                [
                    Command.create(
                        {
                            "order": 10,
                            "verb": self._verb("endorse").id,
                            "target_mode": "person",
                            "employee_id": self.emp_c.id,
                        }
                    )
                ],
            )

    def test_remove_active_step_revokes_and_advances(self):
        doc = self._circulating_doc()
        active = self._step(doc, 10)
        self._edit(doc, [Command.delete(active.id)])
        self.assertFalse(active.exists())
        self._assert_no_access(doc, self.user_b)
        self.assertEqual(self._step(doc, 20).state, "active")

    def test_removed_user_reached_elsewhere_keeps_access(self):
        """Taken off one step but still reached through an earlier one — the
        หนังสือ still involves them, so they keep their read."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=5, verb="endorse", user=self.user_b)
        self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(self._step(doc, 5), "complete", self.user_b)
        active = self._step(doc, 10)
        self._edit(doc, [Command.update(active.id, {"employee_id": self.emp_c.id})])
        self.assertIn(self.user_b, doc.reached_user_ids)
        doc.with_user(self.user_b).check_access_rule("read")

    def test_remove_waiting_step_deletes(self):
        doc = self._circulating_doc()
        self._edit(
            doc,
            [
                Command.create(
                    {
                        "order": 30,
                        "verb": self._verb("acknowledge").id,
                        "target_mode": "person",
                        "employee_id": self.emp_c.id,
                    }
                )
            ],
        )
        extra = self._step(doc, 30)
        self._edit(doc, [Command.delete(extra.id)])
        self.assertFalse(extra.exists())

    def test_cannot_remove_issuing_step_when_unnumbered(self):
        doc = self._circulating_doc()
        with self.assertRaises(UserError):
            self._edit(doc, [Command.delete(self._step(doc, 20).id)])

    def test_done_step_is_locked(self):
        doc = self._circulating_doc()
        done = self._step(doc, 10)
        self._act(done, "complete", self.user_b)
        with self.assertRaises(UserError):
            self._edit(doc, [Command.update(done.id, {"employee_id": self.emp_c.id})])
        with self.assertRaises(UserError):
            self._edit(doc, [Command.delete(done.id)])

    def test_requires_route_editor_group(self):
        doc = self._circulating_doc()
        waiting = self._step(doc, 20)
        for user in (self.manager, self.user_a):
            with self.assertRaises(UserError):
                self._edit(
                    doc,
                    [Command.update(waiting.id, {"employee_id": self.emp_c.id})],
                    user=user,
                )

    def test_refresh_route_holders(self):
        doc = self._make_doc(sender=self.user_b)
        self._add_step(
            doc,
            order=10,
            verb="sign_approve",
            target_mode="position",
            position=self.pos,
        )
        doc.action_send()
        active = self._step(doc, 10)
        self.assertEqual(active.actor_user_ids, self.user_a)
        self.pos.holder_ids = [Command.set(self.emp_c.ids)]
        doc.with_user(self.editor).action_refresh_route_holders()
        self.assertEqual(active.actor_user_ids, self.user_c)
        self.assertEqual(self._activity_users(active), self.user_c)
        self._assert_no_access(doc, self.user_a)
        with self.assertRaises(UserError):
            doc.with_user(self.manager).action_refresh_route_holders()

    def test_edit_logged_in_chatter(self):
        doc = self._circulating_doc()
        waiting = self._step(doc, 20)
        count = len(doc.message_ids)
        self._edit(doc, [Command.update(waiting.id, {"employee_id": self.emp_c.id})])
        self.assertGreater(len(doc.message_ids), count)
        self.assertIn(self.emp_c.name, doc.message_ids[0].body)

    def test_engine_context_does_not_bypass_guards(self):
        """No client-settable context switches the guards off (review finding)."""
        doc = self._circulating_doc()
        done = self._step(doc, 10)
        self._act(done, "complete", self.user_b)
        step = done.with_user(self.user_a).with_context(sarabun_route_engine=True)
        with self.assertRaises(UserError):
            step.write({"employee_id": self.emp_c.id})

    def test_added_step_without_actor_raises(self):
        """Replacing the active step with one nobody can act on would strand the
        หนังสือ — refused at save."""
        nobody = self.env["hr.employee"].create({"name": "ไม่มีบัญชีผู้ใช้"})
        vacant = self.Position.create(
            {"name": "ตำแหน่งไร้ผู้ใช้", "holder_ids": [(6, 0, nobody.ids)]}
        )
        doc = self._circulating_doc()
        with self.assertRaisesRegex(UserError, "no holder"):
            self._edit(
                doc,
                [
                    Command.delete(self._step(doc, 10).id),
                    Command.create(
                        {
                            "order": 10,
                            "verb": self._verb("endorse").id,
                            "target_mode": "position",
                            "position_id": vacant.id,
                        }
                    ),
                ],
            )

    def test_pull_back_unaffected(self):
        """The sender's ดึงกลับ recreates the Route while circulating — an engine
        write the guards must let through."""
        doc = self._circulating_doc()
        doc.with_user(self.user_a).action_pull_back("แก้ไข")
        self.assertEqual(doc.state, "returned")

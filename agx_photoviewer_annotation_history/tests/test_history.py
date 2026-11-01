from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from ..hooks import post_init_hook


@tagged("post_install", "-at_install")
class TestAnnotationHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_a = new_test_user(cls.env, login="history_a", groups="base.group_user")
        cls.user_b = new_test_user(cls.env, login="history_b", groups="base.group_user")
        cls.partner = cls.env["res.partner"].create({"name": "Annotated partner"})
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "doc.pdf",
                "raw": b"%PDF-1.4",
                "mimetype": "application/pdf",
                "res_model": "res.partner",
                "res_id": cls.partner.id,
            }
        )
        cls.Annotation = cls.env["ir.attachment.annotation"]
        cls.Event = cls.env["ir.attachment.annotation.event"]

    def _as(self, user, session):
        return self.Annotation.with_user(user).with_context(annotation_session=session)

    def _add(self, user, session, **vals):
        values = {
            "attachment_id": self.attachment.id,
            "page": 1,
            "kind": "check",
            "geometry": {"x": 0.5, "y": 0.5, "size": 0.04},
        }
        values.update(vals)
        return self._as(user, session).annotation_save(values)

    def _events(self):
        return self.Event.search([("attachment_id", "=", self.attachment.id)])

    def test_events_per_operation(self):
        saved = self._add(self.user_a, "s1")
        self._as(self.user_a, "s1").annotation_save(
            {"id": saved["id"], "color": "#000000"}
        )
        # Saving the same values again is not a change.
        self._as(self.user_a, "s1").annotation_save(
            {"id": saved["id"], "color": "#000000"}
        )
        self._as(self.user_a, "s1").annotation_delete(saved["id"])

        events = self._events()
        self.assertEqual(events.mapped("operation"), ["add", "change", "remove"])
        self.assertEqual(set(events.mapped("session_key")), {"s1"})
        self.assertEqual(events.user_id, self.user_a)
        self.assertEqual(set(events.mapped("annotation_id")), {saved["id"]})
        add, change, remove = events
        self.assertFalse(add.before)
        self.assertEqual(add.after["kind"], "check")
        self.assertEqual(change.before["color"], "#e53935")
        self.assertEqual(change.after["color"], "#000000")
        self.assertEqual(remove.before["color"], "#000000")
        self.assertFalse(remove.after)

    def test_history_groups_by_session(self):
        mark = self._add(self.user_a, "s1")
        comment = self._add(
            self.user_b, "s2", kind="comment", geometry={"x": 0.2, "y": 0.2}, text="Fix"
        )
        self._as(self.user_a, "s3").annotation_delete(mark["id"])
        self._as(self.user_b, "s4").annotation_delete(comment["id"])

        history = self.Annotation.with_user(self.user_b).annotation_history(
            self.attachment.id
        )
        self.assertEqual(
            [change["key"] for change in history], ["s1", "s2", "s3", "s4"]
        )
        self.assertEqual(history[0]["user_name"], self.user_a.name)
        self.assertEqual(history[1]["user_name"], self.user_b.name)
        # A removed comment keeps its text in the History.
        removal = history[3]["events"][0]
        self.assertEqual(removal["operation"], "remove")
        self.assertEqual(removal["annotation_id"], comment["id"])
        self.assertEqual(removal["before"]["text"], "Fix")

    def test_history_needs_read_access(self):
        orphan = (
            self.env["ir.attachment"]
            .with_user(self.user_a)
            .create({"name": "orphan.pdf", "raw": b"%PDF-1.4"})
        )
        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.user_b).annotation_history(orphan.id)

    def test_post_init_seeds_existing_annotations(self):
        saved = self._add(self.user_a, "s1")
        self._events().unlink()
        post_init_hook(self.env.cr, self.env.registry)

        event = self._events()
        self.assertEqual(len(event), 1)
        self.assertEqual(event.operation, "add")
        self.assertEqual(event.annotation_id, saved["id"])
        self.assertEqual(event.user_id, self.user_a)
        self.assertTrue(event.session_key.startswith("initial-%s-" % self.user_a.id))
        self.assertEqual(event.after["geometry"], saved["geometry"])

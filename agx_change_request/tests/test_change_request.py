from odoo import fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

ANSWER = "agx_change_request.mail_activity_change_request_answer"
CHECK = "agx_change_request.mail_activity_change_request_check"


class RequestHolder(models.Model):
    """A record taking Change requests."""

    _name = "test.change.request.holder"
    _description = "Test Change Request Holder"
    _inherit = ["mail.thread", "mail.activity.mixin", "change.request.mixin"]

    name = fields.Char()


@tagged("post_install", "-at_install")
class TestChangeRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        RequestHolder._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.change.request.holder"],
            {"module": "agx_change_request"},
        )
        makers = cls.env["res.groups"].create({"name": "Test request makers"})
        model_id = cls.env["ir.model"]._get_id("test.change.request.holder")
        # Everyone reads the record; only makers edit it.
        cls.env["ir.model.access"].create(
            [
                {
                    "name": "holder user",
                    "model_id": model_id,
                    "group_id": cls.env.ref("base.group_user").id,
                    "perm_read": True,
                },
                {
                    "name": "holder maker",
                    "model_id": model_id,
                    "group_id": makers.id,
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": True,
                },
            ]
        )
        cls.reviewer = new_test_user(
            cls.env, login="cr_reviewer", groups="base.group_user"
        )
        cls.maker = new_test_user(cls.env, login="cr_maker", groups="base.group_user")
        cls.maker.groups_id = [(4, makers.id)]
        cls.other = new_test_user(cls.env, login="cr_other", groups="base.group_user")
        cls.admin = new_test_user(
            cls.env, login="cr_admin", groups="base.group_user,base.group_erp_manager"
        )
        cls.holder = cls.env["test.change.request.holder"].create({"name": "Doc"})
        cls.Request = cls.env["change.request"]

    def _make(self, text="VAT total is wrong", assignees=None, user=None):
        return self.Request.with_user(user or self.reviewer).request_create(
            self.holder._name,
            self.holder.id,
            text,
            (assignees or self.maker).ids,
        )

    def _count(self):
        self.holder.invalidate_recordset(["change_request_count"])
        return self.holder.change_request_count

    def _activities(self, request_id, xmlid):
        return self.env["mail.activity"].search(
            [
                ("change_request_id", "=", request_id),
                ("activity_type_id", "=", self.env.ref(xmlid).id),
            ]
        )

    def test_lifecycle(self):
        before = len(self.holder.message_ids)
        made = self._make()
        self.assertEqual(made["state"], "open")
        self.assertEqual(self._count(), 1)
        # The Assignee has an activity to answer it; the step is in the chatter.
        self.assertEqual(self._activities(made["id"], ANSWER).user_id, self.maker)
        self.assertEqual(len(self.holder.message_ids), before + 1)
        self.assertEqual(self.holder.message_ids[0].author_id, self.reviewer.partner_id)
        self.assertIn(self.maker.partner_id, self.holder.message_ids[0].partner_ids)

        # Anyone who reads the record replies; a reply from someone else
        # answers it, clears the Assignee's activity and gives the author one
        # to check the answer.
        answered = self.Request.with_user(self.other).request_reply(
            made["id"], "Fixed in revision 2"
        )
        self.assertEqual(answered["state"], "answered")
        self.assertFalse(self._activities(made["id"], ANSWER))
        self.assertEqual(self._activities(made["id"], CHECK).user_id, self.reviewer)
        # Another answer renews it, never adds a second one.
        self.Request.with_user(self.maker).request_reply(made["id"], "And page 2")
        self.assertEqual(self._activities(made["id"], CHECK).user_id, self.reviewer)
        # Answered is still outstanding.
        self.assertEqual(self._count(), 1)
        # The author replying to an answered request opens it again: the
        # conversation goes on, the Assignee gets the activity back and the
        # author's is cleared.
        reopened = self.Request.with_user(self.reviewer).request_reply(
            made["id"], "Line 3 is still wrong"
        )
        self.assertEqual(reopened["state"], "open")
        self.assertEqual(self._activities(made["id"], ANSWER).user_id, self.maker)
        self.assertFalse(self._activities(made["id"], CHECK))
        answered = self.Request.with_user(self.maker).request_reply(
            made["id"], "Fixed line 3 too"
        )
        self.assertEqual(answered["state"], "answered")
        self.assertEqual(
            [(r["body"], r["by_request_author"]) for r in answered["replies"]],
            [
                ("Fixed in revision 2", False),
                ("And page 2", False),
                ("Line 3 is still wrong", True),
                ("Fixed line 3 too", False),
            ],
        )

        # Only its author (or someone on their behalf) closes it.
        with self.assertRaises(AccessError):
            self.Request.with_user(self.maker).request_set_closed(made["id"], True)
        closed = self.Request.with_user(self.reviewer).request_set_closed(
            made["id"], True
        )
        self.assertEqual(closed["state"], "closed")
        self.assertFalse(
            self.env["mail.activity"].search([("change_request_id", "=", made["id"])])
        )
        self.assertEqual(self._count(), 0)

        with self.assertRaises(UserError):
            self.Request.with_user(self.maker).request_reply(made["id"], "Again")
        # Reopening gives the Assignees their activity back.
        reopened = self.Request.with_user(self.reviewer).request_set_closed(
            made["id"], False
        )
        self.assertEqual(reopened["state"], "open")
        self.assertEqual(self._activities(made["id"], ANSWER).user_id, self.maker)

    def test_steps_signal_the_record_live(self):
        Bus = self.env["bus.bus"]
        channel = '"agx_change_request:%s:%s"' % (self.holder._name, self.holder.id)
        before = Bus.search_count([("channel", "like", channel)])
        made = self._make()
        self.Request.with_user(self.maker).request_reply(made["id"], "Done")
        self.assertEqual(Bus.search_count([("channel", "like", channel)]), before + 2)
        # It says which record changed, nothing of the request itself.
        message = Bus.search([("channel", "like", channel)], order="id desc", limit=1)
        self.assertNotIn("Done", message.message)

    def test_admin_closes_on_behalf(self):
        made = self._make()
        self.assertFalse(
            self.Request.with_user(self.other).request_load(
                self.holder._name, self.holder.id
            )["requests"][0]["can_close"]
        )
        closed = self.Request.with_user(self.admin).request_set_closed(made["id"], True)
        self.assertEqual(closed["state"], "closed")
        self.assertIn("on behalf", self.holder.message_ids[0].body)

    def test_edit_and_delete_any_time(self):
        made = self._make()
        self.Request.with_user(self.maker).request_reply(made["id"], "Done")
        with self.assertRaises(AccessError):
            self.Request.with_user(self.maker).request_update(made["id"], {"text": "x"})
        edited = self.Request.with_user(self.reviewer).request_update(
            made["id"], {"text": "VAT and total are wrong"}
        )
        self.assertEqual(edited["text"], "VAT and total are wrong")
        self.assertEqual(
            [p["text"] for p in edited["previous_texts"]], ["VAT total is wrong"]
        )
        # Re-assigning moves the activity (none here: it is answered).
        self.Request.with_user(self.reviewer).request_update(
            made["id"], {"assignee_ids": self.other.ids}
        )
        self.assertEqual(self.Request.browse(made["id"]).assignee_ids, self.other)

        self.Request.with_user(self.reviewer).request_delete(made["id"])
        self.assertFalse(self.Request.browse(made["id"]).exists())
        self.assertIn("VAT and total are wrong", self.holder.message_ids[0].body)
        self.assertFalse(
            self.env["mail.activity"].search([("change_request_id", "=", made["id"])])
        )

    def test_reassign_open_request(self):
        made = self._make()
        self.Request.with_user(self.reviewer).request_update(
            made["id"], {"assignee_ids": self.other.ids}
        )
        self.assertEqual(self._activities(made["id"], ANSWER).user_id, self.other)

    def test_assignees_follow_the_record(self):
        made = self._make()
        self.assertIn(self.maker.partner_id, self.holder.message_partner_ids)
        # Even when assigned while answered, which schedules no activity.
        self.Request.with_user(self.maker).request_reply(made["id"], "Done")
        self.Request.with_user(self.reviewer).request_update(
            made["id"], {"assignee_ids": (self.maker | self.other).ids}
        )
        self.assertIn(self.other.partner_id, self.holder.message_partner_ids)

    def test_assignee_must_read_the_record(self):
        portal = new_test_user(self.env, login="cr_portal", groups="base.group_portal")
        with self.assertRaises(UserError):
            self._make(assignees=portal)

    def test_record_must_take_requests(self):
        partner = self.env["res.partner"].create({"name": "No requests"})
        with self.assertRaises(UserError):
            self.Request.with_user(self.reviewer).request_create(
                "res.partner", partner.id, "Fix", []
            )

    def test_cancel_and_unlink(self):
        made = self._make()
        request = self.Request.browse(made["id"])
        request._cancel("The file was deleted.")
        self.assertEqual(request.state, "cancelled")
        self.assertEqual(self._count(), 0)
        self.assertFalse(request.activity_ids)
        self.holder.unlink()
        self.assertFalse(request.exists())

import io

from PIL import Image

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


def _png():
    output = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(output, format="PNG")
    return output.getvalue()


class PinHolder(models.Model):
    """A record taking Change requests, with files in a many2many_binary."""

    _name = "test.pinned.request.holder"
    _description = "Test Pinned Request Holder"
    _inherit = ["mail.thread", "mail.activity.mixin", "change.request.mixin"]

    name = fields.Char()
    attachment_ids = fields.Many2many("ir.attachment")


@tagged("post_install", "-at_install")
class TestPinnedRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        PinHolder._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.pinned.request.holder"],
            {"module": "agx_photoviewer_change_request"},
        )
        cls.env["ir.model.access"].create(
            {
                "name": "holder user",
                "model_id": cls.env["ir.model"]._get_id("test.pinned.request.holder"),
                "group_id": cls.env.ref("base.group_user").id,
                "perm_read": True,
            }
        )
        cls.reviewer = new_test_user(
            cls.env, login="pin_reviewer", groups="base.group_user"
        )
        cls.maker = new_test_user(cls.env, login="pin_maker", groups="base.group_user")
        cls.holder = cls.env["test.pinned.request.holder"].create({"name": "Doc"})
        cls.file = cls.env["ir.attachment"].create(
            {
                "name": "quotation.png",
                "raw": _png(),
                "mimetype": "image/png",
                "res_model": "test.pinned.request.holder",
                "res_id": cls.holder.id,
            }
        )
        cls.holder.attachment_ids = [(6, 0, cls.file.ids)]
        cls.Annotation = cls.env["ir.attachment.annotation"]
        cls.Request = cls.env["change.request"]

    def _comment(self, flag=True, text="VAT total is wrong", attachment=None):
        return self.Annotation.with_user(self.reviewer).annotation_save(
            {
                "attachment_id": (attachment or self.file).id,
                "kind": "comment",
                "geometry": {"x": 0.5, "y": 0.5},
                "text": text,
                "change_request": flag,
                "assignee_ids": self.maker.ids,
            }
        )

    def test_comment_is_plain_unless_flagged(self):
        plain = self._comment(flag=False)
        self.assertFalse(plain["change_request"])
        self.assertFalse(plain["request"])
        # Other kinds of Annotation are never Change requests.
        stamp = self.Annotation.with_user(self.reviewer).annotation_save(
            {
                "attachment_id": self.file.id,
                "kind": "check",
                "geometry": {"x": 0.2, "y": 0.2},
                "change_request": True,
            }
        )
        self.assertFalse(stamp["change_request"])
        self.assertFalse(self.Request.search([("res_id", "=", self.holder.id)]))

    def test_pinned_request(self):
        pin = self._comment()
        request = pin["request"]
        self.assertEqual(request["state"], "open")
        self.assertEqual(request["pin"]["annotation_id"], pin["id"])
        self.assertEqual(request["pin"]["file_name"], "quotation.png")
        self.assertEqual([u["id"] for u in request["assignees"]], self.maker.ids)
        self.assertEqual(self.file.outstanding_request_count, 1)
        loaded = self.Annotation.with_user(self.maker).annotation_load(self.file.id)
        self.assertTrue(loaded["can_request"])
        self.assertEqual([r["id"] for r in loaded["requests"]], [request["id"]])
        # Answered and closed like any request; the pin shows its state.
        self.Request.with_user(self.maker).request_respond(request["id"], "Fixed")
        self.Request.with_user(self.reviewer).request_set_closed(request["id"], True)
        loaded = self.Annotation.with_user(self.maker).annotation_load(self.file.id)
        self.assertEqual(loaded["annotations"][0]["request"]["state"], "closed")
        self.assertFalse(loaded["requests"])

    def test_text_follows_the_request(self):
        pin = self._comment()
        self.Request.with_user(self.reviewer).request_update(
            pin["request"]["id"], {"text": "VAT and total are wrong"}
        )
        self.assertEqual(
            self.Annotation.browse(pin["id"]).text, "VAT and total are wrong"
        )
        saved = self.Annotation.with_user(self.reviewer).annotation_save(
            {"id": pin["id"], "text": "Only VAT is wrong"}
        )
        self.assertEqual(saved["request"]["text"], "Only VAT is wrong")
        self.assertEqual(len(saved["request"]["previous_texts"]), 2)

    def test_unflag_and_delete(self):
        pin = self._comment()
        # No longer asking for a fix: the Comment stays, the request goes.
        saved = self.Annotation.with_user(self.reviewer).annotation_save(
            {"id": pin["id"], "change_request": False}
        )
        self.assertFalse(saved["request"])
        self.assertTrue(self.Annotation.browse(pin["id"]).exists())
        self.assertFalse(self.Request.browse(pin["request"]["id"]).exists())
        # Removing the pin of a request deletes the request.
        pin = self._comment()
        self.Annotation.with_user(self.reviewer).annotation_delete(pin["id"])
        self.assertFalse(self.Request.browse(pin["request"]["id"]).exists())
        self.assertIn("VAT total is wrong", self.holder.message_ids[0].body)
        # And deleting the request removes its pin.
        pin = self._comment()
        self.Request.with_user(self.reviewer).request_delete(pin["request"]["id"])
        self.assertFalse(self.Annotation.browse(pin["id"]).exists())

    def test_deleted_file_cancels(self):
        pin = self._comment()
        request = self.Request.browse(pin["request"]["id"])
        self.file.unlink()
        self.assertEqual(request.state, "cancelled")
        self.assertIn("quotation.png", request.cancel_reason)
        formatted = request._format()[0]
        self.assertEqual(formatted["pin"]["file_name"], "quotation.png")
        self.assertFalse(formatted["pin"]["attachment_id"])
        self.assertFalse(request.activity_ids)

    def test_session_note_leaves_requests_out(self):
        pin = self._comment()
        plain = self._comment(flag=False, text="Matches the invoice")
        before = len(self.holder.message_ids)
        self.Annotation.with_user(self.reviewer).annotation_session_note(
            self.file.id, {"added": 1}, [pin["id"], plain["id"]]
        )
        self.assertEqual(len(self.holder.message_ids), before + 1)
        body = self.holder.message_ids[0].body
        self.assertIn("Matches the invoice", body)
        self.assertNotIn("VAT total is wrong", body)

    def test_files_of_other_records_take_no_requests(self):
        partner = self.env["res.partner"].create({"name": "No requests"})
        other = self.env["ir.attachment"].create(
            {
                "name": "other.png",
                "raw": _png(),
                "mimetype": "image/png",
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        loaded = self.Annotation.with_user(self.reviewer).annotation_load(other.id)
        self.assertFalse(loaded["can_request"])
        with self.assertRaises(UserError):
            self._comment(attachment=other)

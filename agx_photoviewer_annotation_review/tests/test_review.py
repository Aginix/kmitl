import io

from PIL import Image

from odoo import fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


def _png(color="white"):
    output = io.BytesIO()
    Image.new("RGB", (200, 100), color).save(output, format="PNG")
    return output.getvalue()


class ReviewHolder(models.Model):
    """A record with a chatter holding files in a many2many_binary field."""

    _name = "test.annotation.review.holder"
    _description = "Test Annotation Review Holder"
    _inherit = ["mail.thread"]

    name = fields.Char()
    attachment_ids = fields.Many2many("ir.attachment")
    locked = fields.Boolean()

    def _annotation_is_locked(self):
        return self.locked


@tagged("post_install", "-at_install")
class TestAnnotationReview(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        ReviewHolder._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.annotation.review.holder"],
            {"module": "agx_photoviewer_annotation_review"},
        )
        model_id = cls.env["ir.model"]._get_id("test.annotation.review.holder")
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
                    "group_id": cls.env.ref("base.group_erp_manager").id,
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": True,
                },
            ]
        )
        cls.maker = new_test_user(
            cls.env,
            login="review_maker",
            groups="base.group_user,base.group_erp_manager",
        )
        cls.reviewer = new_test_user(
            cls.env, login="review_reviewer", groups="base.group_user"
        )
        cls.holder = cls.env["test.annotation.review.holder"].create({"name": "Doc"})
        cls.file = cls.env["ir.attachment"].create(
            {
                "name": "quotation.png",
                "raw": _png(),
                "mimetype": "image/png",
                "res_model": "test.annotation.review.holder",
                "res_id": cls.holder.id,
            }
        )
        cls.holder.attachment_ids = [(6, 0, cls.file.ids)]
        cls.Annotation = cls.env["ir.attachment.annotation"]

    def _request(self, attachment=None, text="VAT total is wrong"):
        return self.Annotation.with_user(self.reviewer).annotation_save(
            {
                "attachment_id": (attachment or self.file).id,
                "kind": "comment",
                "geometry": {"x": 0.5, "y": 0.5},
                "text": text,
                "change_request": True,
            }
        )

    def _revise(self, attachment=None, user=None, color="yellow"):
        return (
            self.env["ir.attachment"]
            .with_user(user or self.maker)
            .browse((attachment or self.file).id)
            ._annotation_create_revision("quotation-v2.png", _png(color), "image/png")
        )

    def test_comment_is_plain_unless_flagged(self):
        plain = self.Annotation.with_user(self.reviewer).annotation_save(
            {
                "attachment_id": self.file.id,
                "kind": "comment",
                "geometry": {"x": 0.1, "y": 0.1},
                "text": "Matches the invoice",
            }
        )
        self.assertFalse(plain["change_request"])
        self.assertFalse(plain["request_state"])
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

    def test_request_lifecycle(self):
        request = self._request()
        self.assertEqual(request["request_state"], "open")
        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.reviewer).annotation_respond(
                request["id"], "Mine"
            )
        answered = self.Annotation.with_user(self.maker).annotation_respond(
            request["id"], "Fixed in revision 2"
        )
        self.assertEqual(answered["request_state"], "answered")
        self.assertEqual(answered["response_name"], self.maker.name)
        # Only its author closes or reopens it.
        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.maker).annotation_set_request_state(
                request["id"], "closed"
            )
        closed = self.Annotation.with_user(self.reviewer).annotation_set_request_state(
            request["id"], "closed"
        )
        self.assertEqual(closed["request_state"], "closed")
        with self.assertRaises(UserError):
            self.Annotation.with_user(self.maker).annotation_respond(
                request["id"], "Again"
            )
        reopened = self.Annotation.with_user(
            self.reviewer
        ).annotation_set_request_state(request["id"], "open")
        self.assertEqual(reopened["request_state"], "open")

    def test_annotated_file_is_not_overwritten(self):
        self._request()
        with self.assertRaises(UserError):
            self.file.write({"raw": _png("red")})
        # Rewriting the same content is fine (e.g. a storage move).
        self.file.write({"raw": self.file.raw})
        # A file nobody annotated may still be replaced.
        other = self.env["ir.attachment"].create({"name": "x.png", "raw": _png()})
        other.write({"raw": _png("red")})

    def test_revision(self):
        request = self._request()
        # Uploading a revision changes the record: read access is not enough.
        with self.assertRaises(AccessError):
            self._revise(user=self.reviewer)
        revision = self._revise()
        self.assertEqual(revision.revision_number, 2)
        self.assertEqual(revision.revision_previous_id, self.file)
        self.assertEqual(revision.create_uid, self.maker)
        self.assertTrue(self.file.revision_superseded)
        # The record shows only the latest revision.
        self.assertEqual(self.holder.attachment_ids, revision)
        self.assertNotIn(self.file, self.holder._get_mail_thread_data_attachments())
        self.assertEqual(self.file._revision_chain(), self.file | revision)
        # Nobody annotates the superseded revision, nor revises it again ...
        with self.assertRaises(UserError):
            self._request()
        with self.assertRaises(UserError):
            self._revise()
        # ... but its open request follows the file and is still answered.
        self.assertEqual(revision.open_request_count, 1)
        loaded = self.Annotation.with_user(self.maker).annotation_load(revision.id)
        self.assertEqual([r["id"] for r in loaded["requests"]], [request["id"]])
        self.assertTrue(loaded["can_revise"])
        self.Annotation.with_user(self.maker).annotation_respond(
            request["id"], "Fixed in revision 2"
        )
        self.assertEqual(
            self.holder._annotation_open_change_requests().mapped("id"),
            [request["id"]],
        )

    def test_revision_of_unsaved_upload(self):
        # Uploaded before the record was saved (res_id 0), held by the field.
        upload = (
            self.env["ir.attachment"]
            .with_user(self.maker)
            .create(
                {
                    "name": "first.png",
                    "raw": _png(),
                    "mimetype": "image/png",
                    "res_model": "test.annotation.review.holder",
                    "res_id": 0,
                }
            )
        )
        holder = self.env["test.annotation.review.holder"].create(
            {"name": "New", "attachment_ids": [(6, 0, upload.ids)]}
        )
        revision = self._revise(upload)
        # Both revisions now belong to the record.
        self.assertEqual((upload | revision).mapped("res_id"), [holder.id] * 2)
        self.assertEqual(holder.attachment_ids, revision)

    def test_locked_record_freezes_requests(self):
        request = self._request()
        self.holder.locked = True
        with self.assertRaises(UserError):
            self.Annotation.with_user(self.maker).annotation_respond(
                request["id"], "Too late"
            )
        with self.assertRaises(UserError):
            self.Annotation.with_user(self.reviewer).annotation_set_request_state(
                request["id"], "closed"
            )
        with self.assertRaises(UserError):
            self._revise()
        self.assertFalse(
            self.Annotation.with_user(self.maker).annotation_load(self.file.id)[
                "can_revise"
            ]
        )

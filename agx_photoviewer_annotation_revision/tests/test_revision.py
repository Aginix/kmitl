import io

from PIL import Image

from odoo import fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


def _png(color="white"):
    output = io.BytesIO()
    Image.new("RGB", (200, 100), color).save(output, format="PNG")
    return output.getvalue()


class RevisionHolder(models.Model):
    """A record with a chatter holding files in a many2many_binary field, and
    listing all its files in a One2many."""

    _name = "test.annotation.revision.holder"
    _description = "Test Annotation Revision Holder"
    _inherit = ["mail.thread"]

    name = fields.Char()
    attachment_ids = fields.Many2many("ir.attachment")
    file_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "test.annotation.revision.holder")],
    )


@tagged("post_install", "-at_install")
class TestAnnotationRevision(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        RevisionHolder._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.annotation.revision.holder"],
            {"module": "agx_photoviewer_annotation_revision"},
        )
        model_id = cls.env["ir.model"]._get_id("test.annotation.revision.holder")
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
            login="revision_maker",
            groups="base.group_user,base.group_erp_manager",
        )
        cls.reviewer = new_test_user(
            cls.env, login="revision_reviewer", groups="base.group_user"
        )
        cls.holder = cls.env["test.annotation.revision.holder"].create({"name": "Doc"})
        cls.file = cls.env["ir.attachment"].create(
            {
                "name": "quotation.png",
                "raw": _png(),
                "mimetype": "image/png",
                "res_model": "test.annotation.revision.holder",
                "res_id": cls.holder.id,
            }
        )
        cls.holder.attachment_ids = [(6, 0, cls.file.ids)]
        cls.Annotation = cls.env["ir.attachment.annotation"]

    def _annotate(self, attachment=None):
        return self.Annotation.with_user(self.reviewer).annotation_save(
            {
                "attachment_id": (attachment or self.file).id,
                "kind": "check",
                "geometry": {"x": 0.5, "y": 0.5},
            }
        )

    def _revise(self, attachment=None, user=None, color="yellow"):
        return (
            self.env["ir.attachment"]
            .with_user(user or self.maker)
            .browse((attachment or self.file).id)
            ._annotation_create_revision("quotation-v2.png", _png(color), "image/png")
        )

    def test_annotated_file_is_not_overwritten(self):
        self._annotate()
        with self.assertRaises(UserError):
            self.file.write({"raw": _png("red")})
        # Rewriting the same content is fine (e.g. a storage move).
        self.file.write({"raw": self.file.raw})
        # A file nobody annotated may still be replaced.
        other = self.env["ir.attachment"].create({"name": "x.png", "raw": _png()})
        other.write({"raw": _png("red")})

    def test_revision(self):
        self._annotate()
        # Uploading a revision changes the record: read access is not enough.
        with self.assertRaises(AccessError):
            self._revise(user=self.reviewer)
        revision = self._revise()
        self.assertEqual(revision.revision_number, 2)
        self.assertEqual(revision.revision_previous_id, self.file)
        self.assertEqual(revision.create_uid, self.maker)
        self.assertTrue(self.file.revision_superseded)
        self.assertEqual(self.file._revision_chain(), self.file | revision)
        # The record shows only the latest revision among its files ...
        self.assertEqual(self.holder.attachment_ids, revision)
        self.assertEqual(self.holder.file_ids, revision)
        # The chatter gets the superseded revision flagged, to leave it out of
        # the record's files but keep it in the messages that hold it.
        thread_files = {
            a["id"]: a.get("revisionSupersededBy")
            for a in self.holder._get_mail_thread_data(["attachments"])["attachments"]
        }
        self.assertEqual(thread_files, {self.file.id: 2, revision.id: None})
        # ... its chatter notes the upload with the new file, and a message
        # keeps the superseded one, marked as such.
        self.assertEqual(self.holder.message_ids[0].attachment_ids, revision)
        formatted = self.file._attachment_format()[0]
        self.assertEqual(formatted["revisionSupersededBy"], 2)
        self.assertNotIn("revisionSupersededBy", revision._attachment_format()[0])
        # Nobody annotates the superseded revision, nor revises it again.
        with self.assertRaises(UserError):
            self._annotate()
        with self.assertRaises(UserError):
            self._revise()
        loaded = self.Annotation.with_user(self.maker).annotation_load(self.file.id)
        self.assertTrue(loaded["superseded"])
        self.assertTrue(loaded["locked"])
        self.assertEqual([r["number"] for r in loaded["revisions"]], [1, 2])
        self.assertTrue(
            self.Annotation.with_user(self.maker).annotation_load(revision.id)[
                "can_revise"
            ]
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
                    "res_model": "test.annotation.revision.holder",
                    "res_id": 0,
                }
            )
        )
        holder = self.env["test.annotation.revision.holder"].create(
            {"name": "New", "attachment_ids": [(6, 0, upload.ids)]}
        )
        revision = self._revise(upload)
        # Both revisions now belong to the record.
        self.assertEqual((upload | revision).mapped("res_id"), [holder.id] * 2)
        self.assertEqual(holder.attachment_ids, revision)

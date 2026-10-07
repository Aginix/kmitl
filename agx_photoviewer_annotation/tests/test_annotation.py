import base64
import io

from PIL import Image
from reportlab.pdfgen import canvas

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged
from odoo.tools.pdf import PdfFileReader


def _pdf(pages=2):
    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    for index in range(pages):
        can.drawString(100, 700, "Page %s" % (index + 1))
        can.showPage()
    can.save()
    return packet.getvalue()


def _png():
    output = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(output, format="PNG")
    return output.getvalue()


@tagged("post_install", "-at_install")
class TestAnnotation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_a = new_test_user(cls.env, login="annot_a", groups="base.group_user")
        cls.user_b = new_test_user(cls.env, login="annot_b", groups="base.group_user")
        cls.partner = cls.env["res.partner"].create({"name": "Annotated partner"})
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "doc.pdf",
                "datas": base64.b64encode(_pdf()),
                "mimetype": "application/pdf",
                "res_model": "res.partner",
                "res_id": cls.partner.id,
            }
        )
        cls.Annotation = cls.env["ir.attachment.annotation"]

    def _save(self, user, **vals):
        values = {
            "attachment_id": self.attachment.id,
            "page": 1,
            "kind": "check",
            "geometry": {"x": 0.5, "y": 0.5, "size": 0.04},
        }
        values.update(vals)
        return self.Annotation.with_user(user).annotation_save(values)

    def test_shared_layer_author_only_edit(self):
        saved = self._save(self.user_a)
        self.assertTrue(saved["is_own"])
        self.assertEqual(saved["checksum"], self.attachment.checksum)

        loaded = self.Annotation.with_user(self.user_b).annotation_load(
            self.attachment.id
        )
        self.assertEqual(len(loaded["annotations"]), 1)
        self.assertFalse(loaded["annotations"][0]["is_own"])
        self.assertEqual(loaded["annotations"][0]["author_id"], self.user_a.id)

        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.user_b).annotation_save(
                {"id": saved["id"], "color": "#000000"}
            )
        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.user_b).annotation_delete(saved["id"])

        # Anyone who reads the file may add to the layer.
        self._save(self.user_b, kind="comment", geometry={"x": 0.1, "y": 0.1}, text="B")
        self.assertEqual(self.attachment.annotation_count, 2)

        self.Annotation.with_user(self.user_a).annotation_save(
            {"id": saved["id"], "color": "#000000"}
        )
        self.Annotation.with_user(self.user_a).annotation_delete(saved["id"])
        self.attachment.invalidate_recordset(["annotation_count"])
        self.assertEqual(self.attachment.annotation_count, 1)

    def test_unreadable_attachment(self):
        # An orphan upload (res_id 0) is only readable by its uploader.
        orphan = (
            self.env["ir.attachment"]
            .with_user(self.user_a)
            .create({"name": "orphan.png", "raw": _png(), "mimetype": "image/png"})
        )
        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.user_b).annotation_load(orphan.id)
        with self.assertRaises(AccessError):
            self.Annotation.with_user(self.user_b).annotation_save(
                {"attachment_id": orphan.id, "kind": "check", "geometry": {}}
            )
        # ... and has no chatter to post a session note on.
        self.assertFalse(
            self.Annotation.with_user(self.user_a).annotation_session_note(
                orphan.id, {"added": 1}, []
            )
        )

    def test_cascade_on_attachment_unlink(self):
        saved = self._save(self.user_a)
        self.attachment.unlink()
        self.assertFalse(self.Annotation.browse(saved["id"]).exists())

    def test_session_note(self):
        comment = self._save(
            self.user_b, kind="comment", geometry={"x": 0.2, "y": 0.2}, text="Fix this"
        )
        before = len(self.partner.message_ids)
        self.assertTrue(
            self.Annotation.with_user(self.user_b).annotation_session_note(
                self.attachment.id, {"added": 1}, [comment["id"]]
            )
        )
        message = self.partner.message_ids[0]
        self.assertEqual(len(self.partner.message_ids), before + 1)
        self.assertEqual(message.author_id, self.user_b.partner_id)
        self.assertTrue(message.subtype_id.internal)
        self.assertIn("Fix this", message.body)

    def test_export_pdf(self):
        self._save(self.user_a, kind="pen", geometry={"points": [[0, 0], [1, 1]]})
        self._save(
            self.user_a,
            page=2,
            kind="rect",
            geometry={"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.2},
        )
        self._save(
            self.user_b, kind="comment", geometry={"x": 0.3, "y": 0.3}, text="ตรวจสอบ"
        )
        original = self.attachment.raw
        pdf = self.Annotation._export_pdf(self.attachment.sudo())
        # Two source pages + one comment summary page.
        self.assertEqual(PdfFileReader(io.BytesIO(pdf), strict=False).getNumPages(), 3)
        # The original file is untouched.
        self.attachment.invalidate_recordset(["raw"])
        self.assertEqual(self.attachment.raw, original)

    def test_export_image(self):
        image = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "raw": _png(),
                "mimetype": "image/png",
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        self.Annotation.with_user(self.user_a).annotation_save(
            {
                "attachment_id": image.id,
                "kind": "highlight",
                "geometry": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3},
            }
        )
        pdf = self.Annotation._export_pdf(image.sudo())
        self.assertEqual(PdfFileReader(io.BytesIO(pdf), strict=False).getNumPages(), 1)

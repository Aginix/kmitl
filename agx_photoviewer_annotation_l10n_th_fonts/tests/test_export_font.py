import io

from PIL import Image

from odoo.tests.common import TransactionCase, tagged


def _png():
    output = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(output, format="PNG")
    return output.getvalue()


@tagged("post_install", "-at_install")
class TestExportFont(TransactionCase):
    def test_thai_comments_page(self):
        partner = self.env["res.partner"].create({"name": "Holder"})
        image = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "raw": _png(),
                "mimetype": "image/png",
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        Annotation = self.env["ir.attachment.annotation"]
        Annotation.annotation_save(
            {
                "attachment_id": image.id,
                "kind": "comment",
                "geometry": {"x": 0.3, "y": 0.3},
                "text": "ยอดรวมไม่ตรง",
            }
        )
        pdf = Annotation._export_pdf(image)
        # The comments page embeds the Thai font.
        self.assertIn(b"THSarabunNew", pdf)

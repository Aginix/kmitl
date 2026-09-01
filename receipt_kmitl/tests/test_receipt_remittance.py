# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo.tools.pdf import PdfFileReader

from .common import ReceiptKmitlCommon

# 1x1 transparent PNG, used to exercise the image-to-PDF attachment path.
TEST_PNG_B64 = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    b"+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestReceiptRemittance(ReceiptKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept_a_child = cls.env["account.analytic.account"].create(
            {
                "name": "Department A / Sub",
                "code": "01-1",
                "plan_id": cls.dept_plan.id,
                "parent_id": cls.dept_a.id,
            }
        )

    def test_full_flow(self):
        r1 = self._make_receipt()
        r2 = self._make_receipt()

        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(set(remittance.receipt_ids.ids), {r1.id, r2.id})

        remittance.action_submit()
        self.assertEqual(remittance.state, "submitted")
        self.assertEqual(r1.state, "submitted")
        self.assertEqual(r2.state, "submitted")

        remittance.action_approve()
        self.assertEqual(remittance.state, "approved")
        self.assertEqual(r1.state, "approved")
        self.assertEqual(r2.state, "approved")

        remittance.action_post()
        self.assertEqual(remittance.state, "posted")
        self.assertEqual(r1.state, "done")
        self.assertEqual(r2.state, "done")
        self.assertTrue(r1.move_id)
        self.assertTrue(r2.move_id)
        self.assertNotEqual(r1.move_id, r2.move_id)

    def test_pull_appends_to_existing_set(self):
        r1 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(set(remittance.receipt_ids.ids), {r1.id})

        # A receipt that becomes pending afterwards is added to the batch,
        # not swapped in to replace the ones already pulled.
        r2 = self._make_receipt()
        remittance.action_pull_pending_receipts()
        self.assertEqual(set(remittance.receipt_ids.ids), {r1.id, r2.id})
        self.assertEqual(r1.remittance_id, remittance)

    def test_pull_gathers_subtree(self):
        r_parent = self._make_receipt(department=self.dept_a)
        r_child = self._make_receipt(department=self.dept_a_child)
        r_other = self._make_receipt(department=self.dept_b)

        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.action_pull_pending_receipts()
        self.assertEqual(
            set(remittance.receipt_ids.ids), {r_parent.id, r_child.id}
        )
        self.assertNotIn(r_other.id, remittance.receipt_ids.ids)

    def test_removing_receipt_returns_it_to_pool(self):
        r1 = self._make_receipt()
        r2 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        remittance.action_submit()

        remittance.write({"receipt_ids": [(3, r1.id)]})
        self.assertFalse(r1.remittance_id)
        self.assertEqual(r1.state, "draft")
        self.assertEqual(remittance.state, "submitted")

    def test_cancel_releases_receipts(self):
        r1 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_cancel()
        self.assertEqual(remittance.state, "cancelled")
        self.assertFalse(r1.remittance_id)
        self.assertEqual(r1.state, "draft")

    def test_posted_cannot_be_cancelled(self):
        r1 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_approve()
        remittance.action_post()
        with self.assertRaises(UserError):
            remittance.action_cancel()

    def test_reset_to_draft_from_submitted(self):
        r1 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        remittance.action_submit()
        remittance.action_draft()
        self.assertEqual(remittance.state, "draft")
        self.assertEqual(r1.state, "draft")

    def test_submit_rejects_receipt_outside_subtree(self):
        r_other = self._make_receipt(department=self.dept_b)
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r_other.id])],
            }
        )
        with self.assertRaises(ValidationError):
            remittance.action_submit()

    def test_build_attachments_pdf_no_attachments(self):
        r1 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        pdf_content = remittance._build_attachments_pdf()
        self.assertTrue(pdf_content)

    def test_build_attachments_pdf_with_attachments(self):
        r1 = self._make_receipt()
        r2 = self._make_receipt()
        image_attachment = self.env["ir.attachment"].create(
            {
                "name": "slip.png",
                "datas": TEST_PNG_B64,
                "mimetype": "image/png",
            }
        )
        skipped_attachment = self.env["ir.attachment"].create(
            {
                "name": "notes.docx",
                "datas": base64.b64encode(b"not really a docx"),
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
            }
        )
        r1.attachment_ids = [(6, 0, [image_attachment.id, skipped_attachment.id])]
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        pdf_content = remittance._build_attachments_pdf()
        self.assertTrue(pdf_content)
        reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)
        # separator(r1) + image page + separator(r2) = 3
        self.assertEqual(reader.getNumPages(), 3)

    def test_build_attachments_pdf_page_alignment(self):
        """Separator pages: one per receipt, plus one page per attachment
        page — r1 has one image (1 page), r2 has none."""
        r1 = self._make_receipt()
        r2 = self._make_receipt()
        image_attachment = self.env["ir.attachment"].create(
            {
                "name": "slip.png",
                "datas": TEST_PNG_B64,
                "mimetype": "image/png",
            }
        )
        r1.attachment_ids = [(6, 0, [image_attachment.id])]
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        pdf_content = remittance._build_attachments_pdf()
        reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)
        self.assertEqual(reader.getNumPages(), 3)

    def test_separator_renders_skipped_attachment_names(self):
        r1 = self._make_receipt()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "receipt_kmitl.action_report_receipt_kmitl_attachments_separator",
            r1.ids,
            data={"skipped_map": {str(r1.id): ["notes.docx"]}},
        )[0]
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        self.assertIn("notes.docx", html)

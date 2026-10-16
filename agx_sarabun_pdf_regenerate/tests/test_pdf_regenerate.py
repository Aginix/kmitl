"""Regenerate the frozen ฉบับลงนาม (ADR-0019)."""

import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestSarabunPdfRegenerate(SarabunCommon):
    def _render(self, content):
        return patch.object(
            type(self.env["sarabun.document"]),
            "_render_official_pdf",
            return_value=content,
        )

    def _completed_doc(self):
        doc = self._make_doc(sender=self.user_b)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        with self._render(b"%PDF-1.4 v1"):
            doc.action_send()
            self._act(self._active_step(doc), "complete", self.user_a)
        self.assertEqual(doc.state, "completed")
        return doc

    def _copies(self, doc):
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", doc._name),
                ("res_id", "=", doc.id),
                ("mimetype", "=", "application/pdf"),
            ]
        )

    def test_regenerate_replaces_signed_pdf(self):
        doc = self._completed_doc()
        self.assertEqual(len(self._copies(doc)), 1)
        with self._render(b"%PDF-1.4 v2"):
            doc.with_user(self.manager).action_regenerate_signed_pdf()
        self.assertTrue(doc.is_frozen)
        self.assertEqual(base64.b64decode(doc.signed_pdf), b"%PDF-1.4 v2")
        copies = self._copies(doc)
        self.assertEqual(len(copies), 1, "the old copy is replaced, not kept")
        self.assertEqual(base64.b64decode(copies.datas), b"%PDF-1.4 v2")

    def test_regenerate_requires_manager(self):
        doc = self._completed_doc()
        with self.assertRaises(UserError):
            doc.with_user(self.user_b).action_regenerate_signed_pdf()

    def test_regenerate_requires_completed(self):
        doc = self._make_doc(sender=self.user_b)
        with self.assertRaises(UserError):
            doc.with_user(self.manager).action_regenerate_signed_pdf()

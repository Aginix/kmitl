# -*- coding: utf-8 -*-
"""P1 — core data model: kind/type split, position holders, references, enclosures."""
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP1DataModel(SarabunCommon):
    def test_kind_and_type_are_separate_fields(self):
        """kind (behaviour axis) is distinct from the config type record."""
        doc = self._make_doc()  # from_record type
        self.assertEqual(doc.kind, "from_record")
        self.assertEqual(doc.kind, doc.type_id.kind)

        memo_type = self.env["sarabun.document.type"].create(
            {"name": "บันทึกข้อความทดสอบ", "kind": "memo"}
        )
        memo_doc = self._make_doc(doc_type=memo_type)
        self.assertEqual(memo_doc.kind, "memo")
        self.assertNotEqual(doc.kind, memo_doc.kind)

    def test_position_holder_resolution(self):
        """A Position resolves to its current holder set."""
        self.assertEqual(self.pos._current_holder_users(), self.user_a)
        self.assertEqual(
            self.pos_multi._current_holder_users(), self.user_a | self.user_b
        )

    def test_references_documents_and_free_text_lines(self):
        """อ้างถึง = m2m prior docs + ordered free-text lines."""
        prior = self._make_doc(subject="หนังสือก่อนหน้า")
        doc = self._make_doc()
        doc.reference_document_ids = [(6, 0, prior.ids)]
        doc.reference_line_ids = [
            (0, 0, {"sequence": 20, "text": "หนังสือ อว 6801/2 ลว 2 พ.ค."}),
            (0, 0, {"sequence": 10, "text": "หนังสือ อว 6801/1 ลว 1 พ.ค."}),
        ]
        self.assertIn(prior, doc.reference_document_ids)
        self.assertEqual(len(doc.reference_line_ids), 2)
        first = doc.reference_line_ids.sorted("sequence")[0]
        self.assertEqual(first.sequence, 10)
        self.assertEqual(first.text, "หนังสือ อว 6801/1 ลว 1 พ.ค.")

    def test_enclosure_ordering(self):
        """สิ่งที่ส่งมาด้วย entries carry an order + caption."""
        doc = self._make_doc()
        doc.enclosure_ids = [
            (0, 0, {"sequence": 30, "description": "ภาคผนวก ค"}),
            (0, 0, {"sequence": 10, "description": "ภาคผนวก ก"}),
            (0, 0, {"sequence": 20, "description": "ภาคผนวก ข"}),
        ]
        ordered = doc.enclosure_ids.sorted("sequence")
        self.assertEqual(
            ordered.mapped("description"),
            ["ภาคผนวก ก", "ภาคผนวก ข", "ภาคผนวก ค"],
        )

    def test_from_record_numbering_must_be_auto(self):
        """from_record documents register automatically — non-auto modes are rejected."""
        doc = self._make_doc()
        self.assertEqual(doc.numbering_mode, "auto")
        with self.assertRaises(ValidationError):
            doc.numbering_mode = "manual"
            doc.flush_recordset()

    def test_content_body_is_editable_rich_text(self):
        """The หนังสือ carries its own rich-text body (เนื้อหา), editable while draft."""
        doc = self._make_doc(content="<p>เรียนเพื่อโปรดพิจารณาอนุมัติ</p>")
        self.assertIn("โปรดพิจารณา", doc.content)
        self.assertTrue(doc.is_editable)  # draft is editable

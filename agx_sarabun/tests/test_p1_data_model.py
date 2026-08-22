# -*- coding: utf-8 -*-
"""P1 — core data model: kind/type split, position holders, references, enclosures."""
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP1DataModel(SarabunCommon):
    def test_kind_and_type_are_separate_fields(self):
        """kind (behaviour axis) is distinct from the config type record."""
        origin = self.Origin.create({"name": "ต้นทางทดสอบ", "test_department_id": self.dept.id})
        doc = self._make_doc(doc_type=self.doc_type_from_record, origin=origin)
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

    def test_enclosure_attachments(self):
        """สิ่งที่ส่งมาด้วย = plain files attached to the หนังสือ (ir.attachment)."""
        doc = self._make_doc()
        atts = self.env["ir.attachment"].create([
            {"name": "ภาคผนวก-ก.pdf", "res_model": "sarabun.document", "res_id": doc.id},
            {"name": "ภาคผนวก-ข.pdf", "res_model": "sarabun.document", "res_id": doc.id},
        ])
        doc.enclosure_attachment_ids = [(6, 0, atts.ids)]
        self.assertEqual(doc.enclosure_attachment_ids, atts)
        self.assertEqual(
            sorted(doc.enclosure_attachment_ids.mapped("name")),
            ["ภาคผนวก-ก.pdf", "ภาคผนวก-ข.pdf"],
        )

    def test_from_record_numbering_must_be_auto(self):
        """from_record documents register automatically — non-auto modes are rejected."""
        origin = self.Origin.create({"name": "ต้นทางทดสอบ", "test_department_id": self.dept.id})
        doc = self._make_doc(doc_type=self.doc_type_from_record, origin=origin)
        self.assertEqual(doc.numbering_mode, "auto")
        with self.assertRaises(ValidationError):
            doc.numbering_mode = "reserved"
            doc.flush_recordset()

    def test_content_body_is_editable_rich_text(self):
        """The หนังสือ carries its own rich-text body (เนื้อหา), editable while draft."""
        doc = self._make_doc(content="<p>เรียนเพื่อโปรดพิจารณาอนุมัติ</p>")
        self.assertIn("โปรดพิจารณา", doc.content)
        self.assertTrue(doc.is_editable)  # draft is editable

    # === allow_manual constraint (P1 — ADR) ===

    def test_allow_manual_default_by_kind(self):
        """allow_manual is False for from_record types, True for memo/circular."""
        self.assertFalse(self.doc_type_from_record.allow_manual)
        self.assertTrue(self.env.ref("agx_sarabun.document_type_memo").allow_manual)
        self.assertTrue(self.env.ref("agx_sarabun.document_type_circular").allow_manual)

    def test_allow_manual_can_be_overridden_and_survives_save(self):
        """allow_manual is stored + readonly=False, so a manual override persists."""
        memo_type = self.env["sarabun.document.type"].create(
            {"name": "บันทึกพิเศษ", "kind": "memo"}
        )
        self.assertTrue(memo_type.allow_manual)
        memo_type.allow_manual = False
        memo_type.flush_recordset()
        memo_type.invalidate_recordset()
        self.assertFalse(memo_type.allow_manual)

    def test_allow_manual_recomputed_when_kind_changes(self):
        """Changing kind re-derives allow_manual from the new kind value."""
        doc_type = self.env["sarabun.document.type"].create(
            {"name": "ทดสอบ kind switch", "kind": "memo"}
        )
        self.assertTrue(doc_type.allow_manual)
        doc_type.kind = "from_record"
        doc_type.flush_recordset()
        doc_type.invalidate_recordset()
        self.assertFalse(doc_type.allow_manual)

    def test_from_record_without_origin_raises_validation_error(self):
        """Creating a from_record document with no origin_model violates the constraint."""
        with self.assertRaises(ValidationError):
            self.Doc.create({
                "subject": "หนังสือไม่มีต้นทาง",
                "type_id": self.doc_type_from_record.id,
                "sender_department_id": self.dept.id,
            })

    def test_from_record_with_origin_passes_constraint(self):
        """A from_record document that carries an origin_model satisfies the constraint."""
        origin = self.Origin.create({"name": "ต้นทางถูกต้อง", "test_department_id": self.dept.id})
        doc = self._make_doc(doc_type=self.doc_type_from_record, origin=origin)
        self.assertEqual(doc.origin_model, origin._name)
        self.assertEqual(doc.kind, "from_record")

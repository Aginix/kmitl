# -*- coding: utf-8 -*-
"""P1 — core data model: kind/type split, position holders, references, enclosures."""
from odoo.exceptions import ValidationError
from odoo.tests.common import Form, tagged

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
        doc = self._make_doc()
        self.assertEqual(doc.numbering_mode, "auto")
        with self.assertRaises(ValidationError):
            doc.numbering_mode = "reserved"
            doc.flush_recordset()

    def test_content_body_is_editable_rich_text(self):
        """The หนังสือ carries its own rich-text body (เนื้อหา), editable while draft."""
        doc = self._make_doc(content="<p>เรียนเพื่อโปรดพิจารณาอนุมัติ</p>")
        self.assertIn("โปรดพิจารณา", doc.content)
        self.assertTrue(doc.is_editable)  # draft is editable

    def test_origin_model_id_only_for_from_record_type(self):
        """origin_model_id is meaningless outside kind = from_record."""
        origin_model = self.env["ir.model"]._get("test.sarabun.origin")
        with self.assertRaises(ValidationError):
            self.env["sarabun.document.type"].create({
                "name": "ประเภททดสอบ", "kind": "memo", "origin_model_id": origin_model.id,
            })

    def test_route_template_origin_model_must_match_type(self):
        """A template bound to a type with a declared origin model can't point elsewhere."""
        origin_model = self.env["ir.model"]._get("test.sarabun.origin")
        typed = self.env["sarabun.document.type"].create({
            "name": "ประเภทผูกโมเดล", "kind": "from_record", "origin_model_id": origin_model.id,
        })
        with self.assertRaises(ValidationError):
            self.Template.create({
                "name": "แม่แบบผิดโมเดล",
                "document_type_id": typed.id,
                "origin_model": "res.partner",
            })

    def test_route_template_origin_model_autofills_from_type(self):
        """Picking a type that declares a model fills the template's origin_model."""
        origin_model = self.env["ir.model"]._get("test.sarabun.origin")
        typed = self.env["sarabun.document.type"].create({
            "name": "ประเภทผูกโมเดล 2", "kind": "from_record", "origin_model_id": origin_model.id,
        })
        with Form(self.Template) as form:
            form.name = "แม่แบบเติมอัตโนมัติ"
            form.document_type_id = typed
        self.assertEqual(form.origin_model, "test.sarabun.origin")

    def test_document_origin_model_must_match_type(self):
        """A หนังสือ's origin_model must agree with its type's declared origin model."""
        origin_model = self.env["ir.model"]._get("test.sarabun.origin")
        typed = self.env["sarabun.document.type"].create({
            "name": "ประเภทผูกโมเดล 3", "kind": "from_record", "origin_model_id": origin_model.id,
        })
        with self.assertRaises(ValidationError):
            self._make_doc(doc_type=typed, origin_model="res.partner", origin_res_id=1)

    def test_reselecting_route_template_does_not_delete_before_save(self):
        """Regression: re-picking route_template_id (even the SAME value) in a
        Form must not delete the document's real routing steps outside of an
        explicit save. Calling ``unlink()`` imperatively inside an onchange
        resolves the NewId-wrapped records back to their real underlying ids
        and deletes them from the database immediately — before Save/Discard
        ever runs — which is the bug this guards against."""
        template = self.Template.create({
            "name": "เส้นทางทดสอบ",
            "line_ids": [(0, 0, {
                "order": 10, "verb": self._verb("sign_approve").id,
                "target_mode": "person", "employee_id": self.emp_a.id,
            })],
        })
        doc = self._make_doc(route_template_id=template.id)
        doc.action_seed_route_from_template()  # persists real template steps now
        live_step_ids = doc.routing_step_ids.ids
        self.assertEqual(len(live_step_ids), 2)  # originator + template step

        with Form(doc) as form:
            form.route_template_id = template  # re-select the SAME template
            # Must still exist in the DB — no premature real delete mid-onchange.
            self.assertTrue(self.Step.browse(live_step_ids).exists())

        doc.invalidate_recordset()
        self.assertEqual(len(doc.routing_step_ids), 2)  # originator + fresh template step

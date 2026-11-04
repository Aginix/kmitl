from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from odoo.tools.safe_eval import safe_eval

from .common import TypeReaderCommon


@tagged("post_install", "-at_install")
class TestTypeReader(TypeReaderCommon):
    def test_reader_same_ou_reads_but_cannot_write(self):
        doc = self._sent_doc()
        self.assertTrue(self._can_read(doc, self.reader))
        as_reader = doc.with_user(self.reader)
        steps = as_reader.routing_step_ids
        self.assertTrue(steps)
        self.assertTrue(steps.recipient_ids.user_id)
        with self.assertRaises(AccessError):
            as_reader.write({"subject": "x"})
        with self.assertRaises(AccessError):
            steps.filtered(lambda s: s.employee_id == self.emp_b).write({"order": 99})

    def test_reader_other_ou_cannot_read(self):
        doc = self._sent_doc()
        self.assertFalse(self._can_read(doc, self.reader_other_ou))

    def test_non_reader_cannot_read(self):
        doc = self._sent_doc()
        self.assertFalse(self._can_read(doc, self.non_reader))

    def test_type_without_reader_groups_unchanged(self):
        doc = self._sent_doc(
            type_id=self.env.ref("agx_sarabun.document_type_circular").id
        )
        self.assertFalse(self._can_read(doc, self.reader))

    def test_draft_hidden_from_reader(self):
        doc = self._make_doc(sender=self.user_a, operating_unit_id=self.ou_1.id)
        self.assertFalse(self._can_read(doc, self.reader))

    def test_reader_not_reached(self):
        """Read-only like a follower: no Incoming entry, no activity."""
        doc = self._sent_doc()
        self.assertNotIn(self.reader, doc.reached_user_ids)
        self.assertFalse(
            self.env["mail.activity"].search(
                [
                    ("res_model", "=", doc._name),
                    ("res_id", "=", doc.id),
                    ("user_id", "=", self.reader.id),
                ]
            )
        )

    def test_route_access_unchanged(self):
        doc = self._sent_doc()
        doc.message_subscribe(partner_ids=self.non_reader.partner_id.ids)
        self.assertTrue(self._can_read(doc, self.user_a))  # sender
        self.assertTrue(self._can_read(doc, self.user_b))  # reached
        self.assertTrue(self._can_read(doc, self.non_reader))  # follower

    def _menu_visible(self, user):
        menu = self.env.ref(
            "agx_sarabun_document_type_access.menu_sarabun_document_unit"
        )
        return menu.id in self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()

    def test_unit_documents_menu(self):
        """หนังสือของหน่วยงาน lists the reader's types only; hidden from non-readers."""
        doc = self._sent_doc()
        action = self.env.ref(
            "agx_sarabun_document_type_access.action_sarabun_document_unit"
        )
        domain = safe_eval(action.domain, {"uid": self.reader.id})
        self.assertIn(doc, self.Doc.with_user(self.reader).search(domain))
        self.assertTrue(self._menu_visible(self.reader))
        self.assertFalse(self._menu_visible(self.non_reader))

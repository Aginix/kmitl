from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun_document_type_access.tests.common import TypeReaderCommon


@tagged("post_install", "-at_install")
class TestTypeReaderAllOu(TypeReaderCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        all_ou = cls.env.ref(
            "agx_sarabun_operating_unit_access_all.group_all_ou_sarabun_document"
        )
        cls.reader_other_ou.groups_id = [(4, all_ou.id)]
        cls.non_reader.groups_id = [(4, all_ou.id)]

    def test_all_ou_reader_reads_other_ou_read_only(self):
        doc = self._sent_doc()
        self.assertTrue(self._can_read(doc, self.reader_other_ou))
        as_reader = doc.with_user(self.reader_other_ou)
        self.assertTrue(as_reader.routing_step_ids)
        with self.assertRaises(AccessError):
            as_reader.write({"subject": "x"})

    def test_all_ou_still_needs_reader_group(self):
        doc = self._sent_doc()
        self.assertFalse(self._can_read(doc, self.non_reader))

    def test_all_ou_draft_hidden(self):
        doc = self._make_doc(sender=self.user_a, operating_unit_id=self.ou_1.id)
        self.assertFalse(self._can_read(doc, self.reader_other_ou))

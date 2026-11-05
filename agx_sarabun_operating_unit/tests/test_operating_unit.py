from odoo import fields, models
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon

from ..hooks import post_init_hook


class SarabunOuOrigin(models.TransientModel):
    _name = "test.sarabun.ou.origin"
    _description = "Test Sarabun origin with an OU"

    operating_unit_id = fields.Many2one("operating.unit")


@tagged("post_install", "-at_install")
class TestSarabunOperatingUnit(SarabunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        SarabunOuOrigin._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr, ["test.sarabun.ou.origin"], {"module": "agx_sarabun_operating_unit"}
        )
        OU = cls.env["operating.unit"]
        partner = cls.env.company.partner_id
        cls.ou_1 = OU.create(
            {"name": "OU 1", "code": "SBOU1", "partner_id": partner.id}
        )
        cls.ou_2 = OU.create(
            {"name": "OU 2", "code": "SBOU2", "partner_id": partner.id}
        )
        cls.user_a.write(
            {
                "assigned_operating_unit_ids": [(6, 0, cls.ou_1.ids)],
                "default_operating_unit_id": cls.ou_1.id,
            }
        )
        cls.ou_origin = cls.env["test.sarabun.ou.origin"].create(
            {"operating_unit_id": cls.ou_2.id}
        )

    @classmethod
    def tearDownClass(cls):
        # drop the test model, or later classes' registry checks flag its table
        del cls.registry.models["test.sarabun.ou.origin"]
        cls.registry.setup_models(cls.cr)
        super().tearDownClass()

    def test_ou_from_origin(self):
        doc = self._make_doc(origin=self.ou_origin)
        self.assertEqual(doc.operating_unit_id, self.ou_2)

    def test_ou_falls_back_to_creator_default(self):
        doc = self.Doc.with_user(self.user_a).create(
            {
                "subject": "หนังสือ OU",
                "type_id": self.doc_type.id,
                "sender_department_id": self.dept.id,
            }
        )
        self.assertEqual(doc.sudo().operating_unit_id, self.ou_1)

    def test_origin_without_ou_field_keeps_default(self):
        doc = self._make_doc(origin=self.Origin.create({"name": "x"}))
        self.assertEqual(
            doc.operating_unit_id, self.env["res.users"].operating_unit_default_get()
        )

    def test_backfill_hook(self):
        from_origin = self._make_doc(origin=self.ou_origin)
        from_sender = self._make_doc(sender=self.user_a, operating_unit_id=self.ou_2.id)
        self.cr.execute(
            "UPDATE sarabun_document SET operating_unit_id = NULL WHERE id IN %s",
            ((from_origin + from_sender)._ids,),
        )
        (from_origin + from_sender).invalidate_recordset(["operating_unit_id"])
        post_init_hook(self.cr, self.registry)
        self.assertEqual(from_origin.operating_unit_id, self.ou_2)
        self.assertEqual(from_sender.operating_unit_id, self.ou_1)

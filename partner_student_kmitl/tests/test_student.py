# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStudent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.student_type = cls.env.ref("partner_type_kmitl.partner_type_student")

    def test_match_by_student_id_then_national_id(self):
        by_vat = self.Partner.create(
            {
                "name": "สมชาย",
                "partner_type_id": self.student_type.id,
                "vat": "1101700203451",
            }
        )
        self.assertTrue(by_vat.is_student)
        match = self.Partner._kmitl_student_match
        self.assertEqual(match({"65010001": "1101700203451"}), {"65010001": by_vat})
        self.assertEqual(match({"65010001": None}), {})
        by_vat.student_code = "65010001"
        self.assertEqual(
            match({"65010001": None, "65010002": None}), {"65010001": by_vat}
        )

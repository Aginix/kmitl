# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

_GET = "odoo.addons.partner_student_kmitl_api.models.kmitl_student_catalog.requests.get"

ROW = {
    "student_id": 65010001,
    "prename_th": "นาย",
    "first_name_th": "สมชาย",
    "last_name_th": "ใจดี",
    "faculty_name_th": "คณะวิศวกรรมศาสตร์",
    "curriculum_name_th": "วิศวกรรมคอมพิวเตอร์",
    "status": "จบ",
}


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


@tagged("post_install", "-at_install")
class TestStudentCatalog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "partner_student_kmitl_api.api_key", "k"
        )
        cls.Catalog = cls.env["kmitl.student.catalog"]
        cls.Partner = cls.env["res.partner"]
        cls.student_type = cls.env.ref("partner_type_kmitl.partner_type_student")

    def test_fetch_reads_bare_list_and_wrapped_list(self):
        for payload in ([ROW], {"students": [ROW]}):
            with patch(_GET, return_value=_response(payload)) as get:
                rows = self.Catalog.fetch(["65010001", "00000000"])
            self.assertEqual(list(rows), ["65010001"])
            self.assertEqual(get.call_args.kwargs["headers"], {"apikey": "k"})
            self.assertEqual(
                get.call_args.kwargs["params"], {"student_id": ["65010001", "00000000"]}
            )

    def test_fetch_chunks_long_lists(self):
        codes = [str(65000000 + i) for i in range(120)]
        with patch(_GET, return_value=_response([])) as get:
            self.assertEqual(self.Catalog.fetch(codes), {})
        self.assertEqual(get.call_count, 3)

    def test_fetch_unreachable_raises(self):
        with patch(_GET, side_effect=requests.ConnectionError("down")):
            with self.assertRaises(UserError):
                self.Catalog.fetch(["65010001"])

    def test_fetch_without_key_raises(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "partner_student_kmitl_api.api_key", False
        )
        with self.assertRaises(UserError):
            self.Catalog.fetch(["65010001"])

    def test_lookup_names_students_from_the_catalog(self):
        with patch(_GET, return_value=_response([ROW])):
            found = self.Partner._kmitl_student_lookup(["65010001", "00000000"])
        self.assertEqual(
            found,
            {
                "65010001": {
                    "name": "นายสมชาย ใจดี",
                    "student_faculty": "คณะวิศวกรรมศาสตร์",
                    "student_curriculum": "วิศวกรรมคอมพิวเตอร์",
                }
            },
        )

    def test_refresh_from_kmitl(self):
        partner = self.Partner.create(
            {
                "name": "x",
                "partner_type_id": self.student_type.id,
                "student_code": "65010001",
            }
        )
        with patch(_GET, return_value=_response([ROW])):
            partner.action_refresh_from_kmitl()
        self.assertEqual(partner.name, "นายสมชาย ใจดี")
        with patch(_GET, return_value=_response([])):
            with self.assertRaises(UserError):
                partner.action_refresh_from_kmitl()

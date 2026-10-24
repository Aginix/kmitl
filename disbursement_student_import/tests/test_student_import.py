# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import io
from unittest.mock import patch

import xlsxwriter

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


def _thai_id(first12):
    total = sum(int(first12[i]) * (13 - i) for i in range(12))
    return first12 + str((11 - total % 11) % 10)


def _xlsx(rows):
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {"in_memory": True})
    sheet = book.add_worksheet()
    sheet.write_row(0, 0, ["id", "amount", "bank", "acc", "vat", "desc"])
    for rowx, row in enumerate(rows, 1):
        for colx, value in enumerate(row):
            if isinstance(value, str):
                sheet.write_string(rowx, colx, value)
            elif value is not None:
                sheet.write_number(rowx, colx, value)
    book.close()
    return base64.b64encode(buffer.getvalue())


def _looked_up(first):
    return {
        "name": "นาย%s ใจดี" % first,
        "student_faculty": "คณะวิศวกรรมศาสตร์",
        "student_curriculum": "วิศวกรรมคอมพิวเตอร์",
    }


@tagged("post_install", "-at_install")
class TestStudentImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.student_type = cls.env.ref("partner_type_kmitl.partner_type_student")
        cls.requester = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Requester",
                    "login": "dsi_requester",
                    "email": "dsi_requester@example.com",
                    "groups_id": [
                        (4, cls.env.ref("disbursement.group_disbursement_user").id)
                    ],
                }
            )
        )
        cls.ktb = cls.env["res.bank"].create({"name": "Test KTB"})
        cls.scb = cls.env["res.bank"].create({"name": "Test SCB"})
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.known = cls.env["res.partner"].create(
            {
                "name": "นายเก่า มีบัญชี",
                "partner_type_id": cls.student_type.id,
                "student_code": "64010001",
                "bank_ids": [
                    (0, 0, {"acc_number": "1111111111", "bank_id": cls.ktb.id})
                ],
            }
        )

    def _request(self, **vals):
        return (
            self.env["disbursement.request"]
            .with_user(self.requester)
            .create({"partner_type_id": self.student_type.id, **vals})
        )

    def _check(self, request, rows, found=None):
        wizard = (
            self.env["disbursement.student.import"]
            .with_user(self.requester)
            .create(
                {
                    "request_id": request.id,
                    "account_id": self.expense_account.id,
                    "file": _xlsx(rows),
                    "filename": "ta.xlsx",
                }
            )
        )
        # Patched on the registry class: ahead of any lookup override
        # (partner_student_kmitl_api) in the MRO.
        with patch.object(
            type(self.env["res.partner"]),
            "_kmitl_student_lookup",
            return_value=found or {},
        ) as lookup:
            wizard.action_check()
        return wizard, lookup

    def _row(self, wizard, number):
        return wizard.line_ids.filtered(lambda r: r.row_number == number)

    def test_import_resolves_students_and_banks(self):
        request = self._request()
        wizard, fetch = self._check(
            request,
            [
                # known student, blank account -> their existing account
                ["64010001", 1500, "", "", "", "Course A"],
                # new student found by the lookup with a new account (leading zero kept)
                ["65010002", 2000, "Test SCB", "0222222222", "", ""],
                # not found -> skipped
                ["65019999", 900, "Test SCB", "0333333333", "", ""],
                # known student again, new account -> warning (duplicate), still imported
                ["64010001", 500, "Test SCB", "444-4-44444-4", "", "Course B"],
                # new student without any account -> skipped
                ["65010003", 700, "", "", "", ""],
            ],
            found={
                "65010002": _looked_up("ใหม่"),
                "65010003": _looked_up("ไร้บัญชี"),
            },
        )
        # only the student IDs no contact carries are looked up
        self.assertEqual(
            set(fetch.call_args.args[0]), {"65010002", "65019999", "65010003"}
        )
        self.assertEqual(self._row(wizard, 2).status, "warning")
        self.assertEqual(self._row(wizard, 3).status, "ready")
        self.assertEqual(self._row(wizard, 4).status, "skip")
        self.assertEqual(self._row(wizard, 6).status, "skip")
        self.assertEqual(wizard.count_ready, 3)
        self.assertEqual(wizard.amount_ready, 4000)

        wizard.action_import()
        lines = request.line_ids.sorted("id")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines.mapped("amount"), [1500, 2000, 500])
        self.assertEqual(lines[0].partner_bank_id, self.known.bank_ids[:1])
        new = lines[1].partner_id
        self.assertEqual(new.name, "นายใหม่ ใจดี")
        self.assertEqual(new.student_code, "65010002")
        self.assertEqual(new.partner_type_id, self.student_type)
        self.assertEqual(lines[1].partner_bank_id.acc_number, "0222222222")
        self.assertEqual(lines[2].partner_id, self.known)
        self.assertEqual(lines[2].partner_bank_id.bank_id, self.scb)
        self.assertEqual(len(self.known.bank_ids), 2, "the old account is kept")
        self.assertEqual(lines[0].name, "Course A")
        self.assertEqual(lines[1].name, self.expense_account.name)
        self.assertIn("65019999", request.message_ids[0].body)

    def test_import_appends(self):
        request = self._request()
        for amount in (100, 200):
            wizard, _fetch = self._check(
                request, [["64010001", amount, "", "", "", ""]]
            )
            wizard.action_import()
        self.assertEqual(request.line_ids.mapped("amount"), [100, 200])

    def test_national_id(self):
        request = self._request(has_tax=True)
        vat = _thai_id("110170020345")
        other = _thai_id("310170020345")
        wizard, _fetch = self._check(
            request,
            [
                ["64010001", 100, "", "", vat, ""],
                ["64010001", 100, "", "", "1234", ""],
            ],
        )
        self.assertEqual(
            self._row(wizard, 2).message, "Student ID appears more than once"
        )
        self.assertIn("not valid", self._row(wizard, 3).message)
        wizard.action_import()
        self.assertEqual(self.known.vat, vat)

        wizard, _fetch = self._check(request, [["64010001", 100, "", "", other, ""]])
        self.assertIn("differs", self._row(wizard, 2).message)
        wizard.action_import()
        self.assertEqual(
            self.known.vat, vat, "a national ID on record is never overwritten"
        )

    def test_taxable_without_national_id_warns(self):
        request = self._request(has_tax=True)
        wizard, _fetch = self._check(request, [["64010001", 100, "", "", "", ""]])
        self.assertEqual(self._row(wizard, 2).status, "warning")

    def test_match_by_national_id_stamps_student_id(self):
        vat = _thai_id("110170020346")
        manual = self.env["res.partner"].create(
            {
                "name": "สมหญิง",
                "partner_type_id": self.student_type.id,
                "vat": vat,
                "bank_ids": [(0, 0, {"acc_number": "5555555555"})],
            }
        )
        request = self._request()
        wizard, fetch = self._check(request, [["65010009", 100, "", "", vat, ""]])
        fetch.assert_not_called()
        wizard.action_import()
        self.assertEqual(request.line_ids.partner_id, manual)
        self.assertEqual(manual.student_code, "65010009")

    def test_only_draft_student_requests(self):
        other_type = self.env.ref("partner_type_kmitl.partner_type_other")
        request = self._request(partner_type_id=other_type.id)
        self.assertFalse(request.is_student_payee)
        with self.assertRaises(UserError):
            self._check(request, [["64010001", 100, "", "", "", ""]])

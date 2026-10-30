# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDraftPreview(TransactionCase):
    """ดูตัวอย่างเอกสาร: a dry run of the หนังสือ before Create Document, the
    หนังสือ's own preview after."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        today = date.today()
        fiscal_year = cls.env.company.find_daterange_fy(today) or cls.env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY test",
                "date_from": today.replace(month=1, day=1),
                "date_to": today.replace(month=12, day=31),
            }
        )
        # The หนังสือ's issuing ส่วนงาน comes from the current user's employee.
        employee = cls.env.user.employee_id or cls.env["hr.employee"].create(
            {"name": "Requestor", "user_id": cls.env.uid}
        )
        employee.department_id = cls.env["hr.department"].create({"name": "Dept"})
        cls.request = cls.env["approval.request"].create(
            {
                "category_id": cls.env.ref(
                    "agx_approval.approval_category_5102010000"
                ).id,
                "owner_id": employee.id,
                "account_fiscal_year_id": fiscal_year.id,
            }
        )

    def test_dry_run_renders_without_creating_a_document(self):
        Doc = self.env["sarabun.document"].sudo()
        count = Doc.search_count([])
        action = self.request.action_preview_sarabun_document()
        self.assertEqual(action["tag"], "agx_approval_sarabun_draft_preview")
        html = self.request._render_sarabun_draft_preview_html().decode("utf-8")
        self.assertIn("ตัวอย่าง", html)
        self.assertEqual(Doc.search_count([]), count)

    def test_live_document_opens_its_own_preview(self):
        self.request.state = "to_send"
        self.request.action_submit_to_sarabun()
        action = self.request.action_preview_sarabun_document()
        self.assertEqual(action["tag"], "sarabun_pdf_preview")
        self.assertEqual(
            action["params"]["doc_id"], self.request.active_sarabun_document_id.id
        )

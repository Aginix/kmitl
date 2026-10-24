# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestDraftPreview(TwoApproverCommon):
    """ดูตัวอย่างเอกสาร: a dry run of the หนังสือ before Submit to Sarabun, the
    หนังสือ's own preview after (ADR 0007)."""

    def _draft(self):
        dr = self.DR.create(
            {
                "partner_type_id": self.partner.partner_type_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "line",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "partner_id": self.partner.id,
                        },
                    )
                ],
            }
        )
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        return dr

    def test_dry_run_renders_without_creating_a_document(self):
        dr = self._draft()
        Doc = self.env["sarabun.document"].sudo()
        count = Doc.search_count([])
        action = dr.action_preview_sarabun_document()
        self.assertEqual(action["tag"], "disbursement_sarabun_draft_preview")
        html = dr._render_sarabun_draft_preview_html().decode("utf-8")
        self.assertIn(dr._get_sarabun_subject(), html)
        self.assertIn("ตัวอย่าง", html)
        self.assertEqual(Doc.search_count([]), count)

    def test_live_document_opens_its_own_preview(self):
        dr = self._draft()
        dr.action_submit()
        dr.action_submit_to_sarabun()
        action = dr.action_preview_sarabun_document()
        self.assertEqual(action["tag"], "sarabun_pdf_preview")
        self.assertEqual(action["params"]["doc_id"], dr.active_sarabun_document_id.id)

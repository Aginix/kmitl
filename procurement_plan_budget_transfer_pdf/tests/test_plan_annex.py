from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.procurement_plan_budget_transfer.tests.test_procurement_plan_budget_transfer import (  # noqa: E501
    PlanTransferCommon,
)


@tagged("post_install", "-at_install")
class TestPlanAnnex(PlanTransferCommon):
    def test_lines_of_one_plan_collapse_to_one_row(self):
        plan = self._make_plan(5000)
        transfer = self._fund_plan_transfer(plan, 1000)
        transfer.write(
            {
                "line_ids": [
                    Command.create(
                        transfer.to_line_ids[0].copy_data({"amount": 500})[0]
                    )
                ]
            }
        )
        annex = transfer._annex_procurement_plans()
        self.assertEqual(len(annex), 1)
        label, rows = annex[0]
        self.assertIn("โอนเข้า", label)
        self.assertEqual([(p, a) for p, a in rows], [(plan, 1500.0)])

    def test_untagged_transfer_has_no_annex(self):
        transfer = self._fund_plan_transfer(self._make_plan(100), 100)
        transfer.to_line_ids.procurement_plan_analytic_id = False
        self.assertFalse(transfer._annex_procurement_plans())

    def test_pdf_renders_with_annex(self):
        plan = self._make_plan(100)
        transfer = self._fund_plan_transfer(plan, 100)
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "budget_transfer_pdf.report_budget_transfer", transfer.ids
        )
        self.assertIn("รายละเอียดแผนจัดซื้อจัดจ้าง", html.decode())
        self.assertIn(plan.name, html.decode())

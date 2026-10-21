import io
from datetime import date

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.pdf import PdfFileReader

REPORT = "advance_payment_contract_pdf.action_report_advance_payment_contract"


@tagged("post_install", "-at_install")
class TestContractPdf(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )
        cls.agreement = cls.env["advance.payment"].create(
            {
                "employee_id": cls.env.ref("hr.employee_admin").id,
                "loan_amount": 300,
                "loan_type_id": loan_type.id,
                "loan_reason": "Test reason",
                "loan_verifier_id": cls.env.ref("base.user_admin").id,
            }
        )

    def test_draft_contract_has_static_second_page(self):
        pdf, _ = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf(REPORT, self.agreement.ids)
        )
        reader = PdfFileReader(io.BytesIO(pdf), strict=False)
        self.assertEqual(reader.getNumPages(), 2)

    def test_contract_date_th(self):
        self.assertEqual(
            self.agreement._contract_date_th(date(2026, 7, 23)),
            "23 กรกฎาคม 2569",
        )
        self.assertEqual(self.agreement._contract_date_th(False), "")

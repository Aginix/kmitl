import io
from datetime import date

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import file_open
from odoo.tools.pdf import PdfFileReader

REPORT = "advance_payment_contract_pdf.action_report_advance_payment_contract"
# 1x1 transparent PNG
SIGNATURE = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8"
    b"AAAAASUVORK5CYII="
)


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

    def test_draft_contract_ends_with_static_page(self):
        pdf, _ = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf(REPORT, self.agreement.ids)
        )
        reader = PdfFileReader(io.BytesIO(pdf), strict=False)
        # Page 1 may run over when the report CSS (fonts) cannot load, as
        # under --test-enable — so check the last page, not the page count.
        path = (
            "advance_payment_contract_pdf/static/pdf/advance_payment_contract_page2.pdf"
        )
        with file_open(path, "rb") as f:
            static = PdfFileReader(f, strict=False).getPage(0).getContents().getData()
        self.assertGreaterEqual(reader.getNumPages(), 2)
        self.assertEqual(
            reader.getPage(reader.getNumPages() - 1).getContents().getData(), static
        )

    def test_contract_date_th(self):
        self.assertEqual(
            self.agreement._contract_date_th(date(2026, 7, 23)),
            "23 กรกฎาคม 2569",
        )
        self.assertEqual(self.agreement._contract_date_th(False), "")

    def test_thai_distribute(self):
        """Real spaces keep their width in span.rs; markup in the text is
        escaped, never injected."""
        html = self.agreement._contract_thai_distribute("ข้าพเจ้า <b>นาย ก</b>")
        self.assertIn('<span class="rs"> </span>', html)
        self.assertIn("&lt;b&gt;", html)
        self.assertEqual(self.agreement._contract_thai_distribute(False), "")

    def test_signatures_follow_workflow(self):
        """A block carries its signer's signature only once the record is
        past the signer's step — not in draft, and not once cancelled."""
        self.agreement.employee_id.signature = SIGNATURE
        self.agreement.approver_id.employee_id.signature = SIGNATURE
        sigs = self.agreement._contract_signatures()
        self.assertFalse(sigs["borrower"]["signature"])
        self.assertEqual(sigs["borrower"]["date"], "")

        self.agreement.write(
            {"state": "to_approve", "date_submitted": "2026-07-23 03:00:00"}
        )
        sigs = self.agreement._contract_signatures()
        self.assertEqual(sigs["borrower"]["signature"], SIGNATURE)
        self.assertEqual(sigs["borrower"]["date"], "23 กรกฎาคม 2569")
        self.assertFalse(sigs["approver"]["signature"])
        self.assertFalse(sigs["receiver"]["signature"])

        self.agreement.state = "in_progress"
        sigs = self.agreement._contract_signatures()
        self.assertEqual(sigs["approver"]["signature"], SIGNATURE)
        # ใบรับเงิน is always signed and dated by hand.
        self.assertFalse(sigs["receiver"]["signature"])
        self.assertEqual(sigs["receiver"]["date"], "")

        self.agreement.state = "cancel"
        sigs = self.agreement._contract_signatures()
        self.assertFalse(any(sig["signature"] for sig in sigs.values()))

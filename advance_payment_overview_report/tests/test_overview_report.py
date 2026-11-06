from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOverviewReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env["advance.payment.overview.report"]
        cls.ou = cls.env.ref("operating_unit.main_operating_unit")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.borrower = Users.create(
            {"name": "Overview Borrower", "login": "apo_borrower"}
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Overview Borrower", "user_id": cls.borrower.id}
        )
        cls.partner = cls.employee.work_contact_id
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "APO Loan Type"}
        )
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        # Scoped to this test's loan type: other loans may exist.
        cls.domain = [("loan_type_id", "=", cls.loan_type.id)]

    def _loan(self, amount=1000.0, state="in_progress"):
        loan = self.env["advance.payment"].create(
            {
                "employee_id": self.employee.id,
                "loan_amount": amount,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test",
                "operating_unit_id": self.ou.id,
            }
        )
        loan.write({"state": state, "date_submitted": datetime(2026, 11, 2, 3, 0)})
        return loan

    def _request(self, loan, name):
        request = self.env["disbursement.request"].create(
            {
                "payment_type": "advance",
                "advance_payment_id": loan.id,
                "operating_unit_id": self.ou.id,
                "partner_type_id": self.partner.partner_type_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.expense_account.id,
                            "name": "line",
                            "amount": 100.0,
                            "partner_id": self.partner.id,
                        },
                    )
                ],
            }
        )
        request.name = name
        return request

    def _data(self, domain=None, group_by=None):
        return self.Report.get_report_data(
            {"domain": self.domain + (domain or []), "group_by": group_by or []}
        )

    def _rows(self, domain=None):
        return [row for group in self._data(domain)["groups"] for row in group["rows"]]

    def test_one_row_per_loan_with_stacked_requests(self):
        loan = self._loan(amount=1500.0)
        self._request(loan, "DR-APO-0002")
        self._request(loan, "DR-APO-0001")
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["documents"], "DR: DR-APO-0001\nDR: DR-APO-0002"
        )
        self.assertEqual(self._data()["totals"]["loan_amount"], 1500.0)

    def test_search_by_request_number(self):
        loan = self._loan()
        self._loan()
        self._request(loan, "DR-APO-FIND")
        rows = self._rows([("overview_document_number", "ilike", "DR-APO-FIND")])
        self.assertEqual([row["id"] for row in rows], [loan.id])

    def test_draft_and_cancelled_excluded(self):
        draft = self._loan(state="draft")
        cancelled = self._loan(state="cancel")
        live = self._loan()
        ids = [row["id"] for row in self._rows()]
        self.assertIn(live.id, ids)
        self.assertNotIn(draft.id, ids)
        self.assertNotIn(cancelled.id, ids)

    def test_grouping_totals(self):
        self._loan(amount=100.0)
        self._loan(amount=200.0, state="approved")
        data = self._data(group_by=["state", "loan_type_id"])
        self.assertTrue(data["grouped"])
        totals = sorted(g["totals"]["loan_amount"] for g in data["groups"])
        self.assertEqual(totals, [100.0, 200.0])
        self.assertTrue(all(len(g["subgroups"]) == 1 for g in data["groups"]))
        self.assertEqual(data["totals"]["loan_amount"], 300.0)

    def test_print_and_export_actions(self):
        self._loan()
        options = {"domain": self.domain, "facets": ["ปีงบประมาณปัจจุบัน"]}
        for method in ("action_print_pdf", "action_export_xlsx"):
            action = getattr(self.Report, method)(options)
            self.assertEqual(action["type"], "ir.actions.report")
        values = self.env[
            "report.advance_payment_overview_report.overview_pdf"
        ]._get_report_values([], data={"options": options})
        self.assertEqual(values["filter_lines"], ["ปีงบประมาณปัจจุบัน"])

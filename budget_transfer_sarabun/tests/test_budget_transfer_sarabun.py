from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestBudgetTransferSarabun(TransactionCase):
    """Drives the budget.transfer ↔ e-Saraban bridge (ADR-0014) end to end:
    ยืนยัน → สร้างหนังสือ (content + งปม.303 enclosure) → ส่ง → ลงนาม → auto-post,
    and the negative outcomes (ตีกลับ/ปฏิเสธ/ยกเลิกการส่ง)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # --- budget fixtures (mirrors budget_transfer/tests/test_budget_transfer.py) ---
        cls.fy = env["account.fiscal.year"].create(
            {
                "name": "FY-TR-SB",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "TRSB_SRC", "name": "Transfer Src SB", "budget_type": "expense"}
        )
        cls.dst = BA.create(
            {"code": "TRSB_DST", "name": "Transfer Dst SB", "budget_type": "expense"}
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def plan(code, name):
            return Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": name, "code": code}
            )

        def acc(name, code, plan_code, plan_name):
            return AA.create(
                {"name": name, "code": code, "plan_id": plan(plan_code, plan_name).id}
            )

        cls.dept_analytic = acc("Dept SB", "TRSB_DEPT", "departments", "Departments")
        cls.source_analytic = acc("Source SB", "TRSB_SRCM", "sources", "Sources")
        cls.activity = acc("Activity SB", "TRSB_ACT", "activities", "Activities")
        cls.fund = acc("Fund SB", "TRSB_FUND", "funds", "Funds")

        move = env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": cls.fy.id,
                "department_analytic_id": cls.dept_analytic.id,
                "source_analytic_id": cls.source_analytic.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": cls.src.id,
                            "balance": 100_000,
                            "activity_analytic_id": cls.activity.id,
                            "fund_analytic_id": cls.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()

        # --- e-Saraban fixtures ---
        cls.hr_dept = env["hr.department"].create({"name": "กองทดสอบ โอนงบ"})
        env["sarabun.document.sequence"].create(
            {
                "name": "ทะเบียนหนังสือ กองทดสอบ โอนงบ",
                "sender_department_id": cls.hr_dept.id,
            }
        )

        cls.requestor = new_test_user(
            env,
            login="btr_sb_requestor",
            name="ผู้ขอโอนงบ",
            groups="base.group_user,budget.group_budget_user",
        )
        env["hr.employee"].create(
            {
                "name": "ผู้ขอโอนงบ",
                "user_id": cls.requestor.id,
                "department_id": cls.hr_dept.id,
            }
        )

        cls.approver_user = new_test_user(
            env,
            login="btr_sb_approver",
            name="ผู้อนุมัติโอนงบ",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        approver_employee = env["hr.employee"].create(
            {"name": "ผู้อนุมัติโอนงบ", "user_id": cls.approver_user.id}
        )
        # Assign the real holder to the (deliberately holderless) seeded position.
        env.ref(
            "budget_transfer_sarabun.position_budget_transfer_approver"
        ).holder_ids = [Command.set(approver_employee.ids)]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _transfer(self):
        def line(vals, direction):
            vals = dict(vals)
            vals["transfer_direction"] = direction
            vals.setdefault("department_analytic_id", self.dept_analytic.id)
            return Command.create(vals)

        from_line = {
            "account_id": self.src.id,
            "amount": 1000,
            "activity_analytic_id": self.activity.id,
            "fund_analytic_id": self.fund.id,
        }
        to_line = {
            "account_id": self.dst.id,
            "amount": 1000,
            "activity_analytic_id": self.activity.id,
            "fund_analytic_id": self.fund.id,
        }
        return (
            self.env["budget.transfer"]
            .with_user(self.requestor)
            .create(
                {
                    "date": date.today(),
                    "account_fiscal_year_id": self.fy.id,
                    "department_analytic_id": self.dept_analytic.id,
                    "source_analytic_id": self.source_analytic.id,
                    "reason": "test transfer via e-Saraban",
                    "line_ids": [line(from_line, "from"), line(to_line, "to")],
                }
            )
        )

    def _submitted_transfer(self):
        transfer = self._transfer()
        transfer.with_user(self.requestor).action_submit()
        return transfer

    def _submit(self, transfer):
        action = transfer.with_user(self.requestor).action_submit_to_sarabun()
        return self.env["sarabun.document"].browse(action["res_id"])

    def _gating_step(self, document):
        return document.routing_step_ids.filtered("gating")[:1]

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------
    def test_submit_guard_blocks_outside_submitted(self):
        transfer = self._transfer()  # still draft
        self.assertFalse(transfer.with_user(self.requestor).action_submit_to_sarabun())

    def test_submit_creates_document_with_content_and_enclosure(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        self.assertTrue(document)
        self.assertIn(transfer.name, document.subject)
        self.assertTrue(document.content)
        self.assertTrue(
            document.enclosure_attachment_ids,
            "the printed แบบ งปม.303 must be enclosed",
        )
        self.assertEqual(
            document.type_id,
            self.env.ref("budget_transfer_sarabun.document_type_budget_transfer"),
        )

    def test_send_moves_transfer_to_sent(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        self.assertEqual(transfer.state, "sent")
        # A circulating (sent) transfer is locked for editing.
        self.assertFalse(transfer.can_edit)
        # The transfer's own date is hidden and now tracks the letter's
        # ลงวันที่ (stamped at send), not the draft/confirm date.
        self.assertEqual(transfer.date, document.date)

    def test_completion_auto_posts_and_stamps_approver(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        step = self._gating_step(document)
        self.assertTrue(step, "the seeded approval step must be gating")
        step.act_on_step("complete", None, actor=self.approver_user)
        transfer.invalidate_recordset()
        self.assertEqual(transfer.state, "posted")
        self.assertEqual(transfer.move_id.state, "posted")
        self.assertEqual(transfer.approver_id, self.approver_user)
        self.assertTrue(transfer.approval_date)

    def test_rejected_never_posts_and_cancels_move(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        step = self._gating_step(document)
        step.act_on_step("reject", {"note": "งบไม่เพียงพอ"}, actor=self.approver_user)
        transfer.invalidate_recordset()
        self.assertEqual(transfer.state, "rejected")
        self.assertEqual(transfer.move_id.state, "cancel")

    def test_returned_reopens_the_transfer(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        step = self._gating_step(document)
        step.act_on_step(
            "return", {"note": "ขอข้อมูลเพิ่ม", "destination": "sender_restart"},
            actor=self.approver_user,
        )
        transfer.invalidate_recordset()
        self.assertEqual(transfer.state, "returned")
        self.assertNotEqual(transfer.state, "posted")
        # The bridge reopens editing in `returned` (extends _compute_can_edit);
        # the base would leave it locked (editable in draft only).
        self.assertTrue(transfer.can_edit)

    def test_cancelled_send_falls_back_to_submitted(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        document.with_user(self.requestor).action_recall(reason="ยกเลิกการส่ง")
        transfer.invalidate_recordset()
        self.assertEqual(transfer.state, "submitted")

    def test_manual_approve_fallback_still_available(self):
        # ADR-0014: the manual approve-and-post button stays visible alongside
        # the letter (only two Budget Managers at KMITL).
        manager = new_test_user(
            self.env,
            login="btr_sb_manager",
            name="ผจก โอนงบ",
            groups="base.group_user,budget.group_budget_manager",
        )
        transfer = self._submitted_transfer()
        transfer.with_user(manager).action_approve()
        self.assertEqual(transfer.state, "posted")

    # ------------------------------------------------------------------
    # extra guards this bridge adds on top of the base's action methods
    # (the base has no notion of `sent`/`returned`/`rejected` at all)
    # ------------------------------------------------------------------
    def test_cancel_blocked_from_sent(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        self.assertEqual(transfer.state, "sent")
        with self.assertRaises(UserError):
            transfer.action_cancel()

    def test_reset_to_draft_blocked_from_sent(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        with self.assertRaises(UserError):
            transfer.action_reset_to_draft()

    def test_reset_to_draft_from_rejected_requires_manager(self):
        manager = new_test_user(
            self.env,
            login="btr_sb_manager2",
            name="ผจก โอนงบ 2",
            groups="base.group_user,budget.group_budget_manager",
        )
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        step = self._gating_step(document)
        step.act_on_step("reject", {"note": "งบไม่เพียงพอ"}, actor=self.approver_user)
        transfer.invalidate_recordset()
        self.assertEqual(transfer.state, "rejected")
        with self.assertRaises(UserError):
            transfer.with_user(self.requestor).action_reset_to_draft()
        transfer.with_user(manager).action_reset_to_draft()
        self.assertEqual(transfer.state, "draft")

    def test_approve_and_post_blocked_outside_submitted(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        self.assertEqual(transfer.state, "sent")
        with self.assertRaises(UserError):
            transfer.action_approve()
        with self.assertRaises(UserError):
            transfer.action_post()

    def test_button_visibility_for_returned_and_rejected(self):
        transfer = self._submitted_transfer()
        document = self._submit(transfer)
        document.with_user(self.requestor).action_send()
        step = self._gating_step(document)
        step.act_on_step(
            "return", {"note": "ขอข้อมูลเพิ่ม", "destination": "sender_restart"},
            actor=self.approver_user,
        )
        transfer.invalidate_recordset()
        self.assertEqual(transfer.state, "returned")
        self.assertTrue(transfer.show_cancel_button)
        self.assertTrue(
            transfer.with_user(self.requestor).show_reset_button,
            "the requestor may pull their own returned transfer back to draft",
        )

from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTransferLineVisibility(TransactionCase):
    """A transfer authored by one unit onto another unit's department is seen
    by the receiving unit (budget ADR-0011 amendment): central (OU A) moves
    budget to OU B's department, and OU B sees — and can draw on — its TO line,
    but never central's FROM line."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-OU",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        OU = env["operating.unit"]
        partner = env.company.partner_id
        cls.ou_a = OU.create(
            {"name": "Central", "code": "OUT_A", "partner_id": partner.id}
        )
        cls.ou_b = OU.create(
            {"name": "Faculty", "code": "OUT_B", "partner_id": partner.id}
        )

        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "OUT_SRC", "name": "OU Src", "budget_type": "expense"}
        )
        cls.dst = BA.create(
            {"code": "OUT_DST", "name": "OU Dst", "budget_type": "expense"}
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code, plan_code, ous=None):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            vals = {"name": name, "code": code, "plan_id": plan.id}
            if ous:
                vals["operating_unit_ids"] = [Command.set(ous.ids)]
            return AA.create(vals)

        cls.dept_a = acc("Dept A", "OUT_DA", "departments", cls.ou_a)
        cls.dept_b = acc("Dept B", "OUT_DB", "departments", cls.ou_b)
        cls.source = acc("Source", "OUT_SRCM", "sources")
        cls.activity = acc("Activity", "OUT_ACT", "activities")
        cls.fund = acc("Fund", "OUT_FUND", "funds")

        cls.user_b = env["res.users"].create(
            {
                "name": "Faculty budget user",
                "login": "out_budget_user_b",
                "groups_id": [Command.set([env.ref("budget.group_budget_user").id])],
                "operating_unit_ids": [Command.set(cls.ou_b.ids)],
                "default_operating_unit_id": cls.ou_b.id,
            }
        )

    def _appropriate(self, amount):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "operating_unit_id": self.ou_a.id,
                "department_analytic_id": self.dept_a.id,
                "source_analytic_id": self.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.src.id,
                            "balance": amount,
                            "activity_analytic_id": self.activity.id,
                            "fund_analytic_id": self.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()

    def _transfer(self, amount):
        def line(account, dept, direction):
            return Command.create(
                {
                    "transfer_direction": direction,
                    "account_id": account.id,
                    "amount": amount,
                    "department_analytic_id": dept.id,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            )

        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "operating_unit_id": self.ou_a.id,
                "department_analytic_id": self.dept_a.id,
                "source_analytic_id": self.source.id,
                "reason": "central to faculty",
                "line_ids": [
                    line(self.src, self.dept_a, "from"),
                    line(self.dst, self.dept_b, "to"),
                ],
            }
        )

    def test_receiving_unit_sees_only_its_transfer_line(self):
        transfer = self._transfer(1000)
        lines = (
            self.env["budget.move.line"]
            .with_user(self.user_b)
            .search([("move_id", "=", transfer.move_id.id)])
        )
        self.assertEqual(lines, transfer.to_line_ids)

    def test_receiving_unit_can_draw_on_transferred_budget(self):
        self._appropriate(100_000)
        transfer = self._transfer(1000)
        transfer.action_submit()
        transfer.action_approve()  # auto-posts (admin)
        self.assertEqual(transfer.state, "posted")
        available = (
            self.env["budget.controller"]
            .with_user(self.user_b)
            .get_available(
                self.dst,
                {
                    str(self.dept_b.id): 100.0,
                    str(self.source.id): 100.0,
                    str(self.activity.id): 100.0,
                    str(self.fund.id): 100.0,
                },
                self.fy.id,
                self.env.company.id,
            )
        )
        self.assertEqual(available, 1000)

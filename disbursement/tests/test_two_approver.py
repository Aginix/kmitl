# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

_DR = "disbursement.request"


class TwoApproverCommon(TransactionCase):
    """Approvers, dimensions and a signed-request factory, shared with the
    disbursement_budget tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env[_DR]
        AAA = cls.env["account.analytic.account"]
        dep_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_departments")
        src_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_sources")
        fund_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_funds")
        act_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_activities")
        cls.dept = AAA.create({"name": "Dept", "plan_id": dep_plan.id})
        cls.source = AAA.create({"name": "Gov", "plan_id": src_plan.id})
        cls.fund = AAA.create({"name": "Fund", "plan_id": fund_plan.id})
        cls.activity = AAA.create({"name": "Act", "plan_id": act_plan.id})
        cls.partner = cls.env["res.partner"].create({
            "name": "Vendor",
            # submit is guarded on every payee having an account
            "bank_ids": [(0, 0, {"acc_number": "1234567890"})],
        })
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.finance = users.create({
            "name": "Finance Director",
            "login": "ta_finance",
            "email": "ta_finance@example.com",
            "groups_id": [
                (4, cls.env.ref(
                    "disbursement.group_disbursement_finance_director").id)
            ],
        })
        cls.rector = users.create({
            "name": "Rector Delegate",
            "login": "ta_rector",
            "email": "ta_rector@example.com",
            "groups_id": [
                (4, cls.env.ref(
                    "disbursement.group_disbursement_rector_delegate").id)
            ],
        })
        cls.officer = users.create({
            "name": "Officer",
            "login": "ta_officer",
            "email": "ta_officer@example.com",
            "groups_id": [
                (4, cls.env.ref("disbursement.group_disbursement_officer").id)
            ],
        })

    def _make_signed_dr(self):
        dr = self.DR.create({
            "partner_type_id": self.partner.partner_type_id.id,
            "line_ids": [(0, 0, {
                "account_id": self.expense_account.id,
                "name": "line",
                "amount": 100.0,
                "partner_id": self.partner.id,
            })],
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        dr.action_submit()
        with self._patch_circuit_entry():
            dr.action_sign()
        return dr

    def _patch_circuit_entry(self):
        """Stub the circuit entry on the registry class, so a signed request
        stays signed whatever bridge (disbursement_wc routes it to a station)
        is installed."""
        return patch.object(type(self.DR), "_on_signed")


@tagged("post_install", "-at_install")
class TestTwoApprover(TwoApproverCommon):
    """What is left of the old two-approver suite in core: the acts live in
    their own modules, so only what the request itself owns is tested here."""

    def test_cancel_resets_approval(self):
        dr = self._make_signed_dr()
        dr.action_cancel()
        self.assertEqual(dr.state, "cancel")

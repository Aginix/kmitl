# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestPayeeBankWizard(TwoApproverCommon):
    """A requester sees a payee's bank accounts from the draft request and
    adds or corrects them inline (never deletes)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Requester",
                "login": "pbw_requester",
                "email": "pbw_requester@example.com",
                "groups_id": [(4, cls.env.ref("disbursement.group_disbursement_user").id)],
            }
        )
        cls.bank = cls.env["res.bank"].create({"name": "Test Bank"})
        cls.payee = cls.env["res.partner"].create(
            {
                "name": "Payee With Account",
                "partner_type_id": cls.partner.partner_type_id.id,
                "bank_ids": [(0, 0, {"acc_number": "1111111111", "bank_id": cls.bank.id})],
            }
        )

    def _request(self, partner):
        return self.DR.with_user(self.requester).create(
            {
                "partner_type_id": partner.partner_type_id.id,
                "line_ids": [
                    (0, 0, {"account_id": self.expense_account.id, "amount": 100.0, "partner_id": partner.id})
                ],
            }
        )

    def _wizard(self, action, rows):
        return (
            self.env[action["res_model"]]
            .with_user(self.requester)
            .create({"request_id": action["context"]["default_request_id"], "line_ids": rows})
        )

    def test_lists_edits_and_adds_accounts(self):
        dr = self._request(self.payee)
        action = dr.line_ids.action_open_partner_bank_wizard()
        rows = [vals for _cmd, _id, vals in action["context"]["default_line_ids"]]
        existing = self.payee.bank_ids
        self.assertEqual([r["bank_account_id"] for r in rows], existing.ids)
        rows[0]["acc_number"] = "2222222222"
        rows.append(
            {"partner_id": self.payee.id, "bank_id": self.bank.id, "acc_number": "3333333333"}
        )
        self._wizard(action, [(0, 0, r) for r in rows]).action_apply()
        self.assertEqual(existing.acc_number, "2222222222")
        self.assertEqual(
            sorted(self.payee.bank_ids.mapped("acc_number")), ["2222222222", "3333333333"]
        )

    def test_payee_without_account_gets_the_new_one(self):
        payee = self.env["res.partner"].create(
            {"name": "No Account", "partner_type_id": self.partner.partner_type_id.id}
        )
        dr = self._request(payee)
        action = dr.line_ids.action_open_partner_bank_wizard()
        self.assertEqual(action["context"]["default_line_ids"], [])
        self._wizard(
            action,
            [(0, 0, {"partner_id": payee.id, "bank_id": self.bank.id, "acc_number": "4444444444"})],
        ).action_apply()
        self.assertEqual(dr.line_ids.partner_bank_id.acc_number, "4444444444")

    def test_only_payees_and_only_drafts(self):
        dr = self._request(self.payee)
        stranger = self.env["res.partner"].create({"name": "Stranger"})
        action = dr.action_open_partner_bank_wizard()
        with self.assertRaises(UserError):
            self._wizard(
                action,
                [(0, 0, {"partner_id": stranger.id, "bank_id": self.bank.id, "acc_number": "5"})],
            ).action_apply()
        # Any state past draft; cancel skips the dimensions constraint.
        dr.state = "cancel"
        with self.assertRaises(UserError):
            dr.action_open_partner_bank_wizard()

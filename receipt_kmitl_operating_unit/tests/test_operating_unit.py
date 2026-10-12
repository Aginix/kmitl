# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestOperatingUnit(ReceiptKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ou = cls.env["operating.unit"].create(
            {
                "name": "Test OU",
                "code": "TOU",
                "partner_id": cls.company.partner_id.id,
            }
        )
        cls.ou_b = cls.env["operating.unit"].create(
            {
                "name": "Test OU B",
                "code": "TOUB",
                "partner_id": cls.company.partner_id.id,
            }
        )

    def _make_ou_receipt(self, operating_unit=None, department=None):
        return self._make_receipt(
            department=department,
            extra_vals={"operating_unit_id": (operating_unit or self.ou).id},
        )

    def _make_remittance(self, operating_unit=None, receipts=None):
        vals = {
            "department_analytic_id": self.dept_a.id,
            "operating_unit_id": (operating_unit or self.ou).id,
            "approver_id": self.env.ref("base.user_root").id,
        }
        if receipts is not None:
            vals["receipt_ids"] = [Command.set(receipts.ids)]
        return self.env["kmitl.receipt.remittance"].create(vals)

    def test_posted_receipt_stamps_ou_on_move_header_and_lines(self):
        receipt = self._make_ou_receipt()
        receipt._action_post()
        self.assertEqual(receipt.move_id.operating_unit_id, self.ou)
        for line in receipt.move_id.line_ids:
            self.assertEqual(line.operating_unit_id, self.ou)

    def test_pull_pending_receipts_excludes_other_operating_unit(self):
        r_mine = self._make_ou_receipt(operating_unit=self.ou)
        r_other = self._make_ou_receipt(operating_unit=self.ou_b)

        remittance = self._make_remittance()
        remittance.action_pull_pending_receipts()

        self.assertEqual(set(remittance.receipt_ids.ids), {r_mine.id})
        self.assertNotIn(r_other.id, remittance.receipt_ids.ids)

    def test_create_report_raises_on_mixed_operating_units(self):
        r_a = self._make_ou_receipt(operating_unit=self.ou, department=self.dept_a)
        r_b = self._make_ou_receipt(operating_unit=self.ou_b, department=self.dept_a)

        with self.assertRaises(UserError):
            (r_a | r_b).action_create_report()

    def test_create_report_sets_operating_unit_from_receipts(self):
        receipt = self._make_ou_receipt()

        action = receipt.action_create_report()
        remittance = self.env["kmitl.receipt.remittance"].browse(action["res_id"])
        self.assertEqual(remittance.operating_unit_id, self.ou)

    def test_submit_raises_on_operating_unit_mismatch(self):
        r_other = self._make_ou_receipt(operating_unit=self.ou_b, department=self.dept_a)

        remittance = self._make_remittance(operating_unit=self.ou, receipts=r_other)
        with self.assertRaises(ValidationError):
            remittance.action_submit()

    def test_approve_updates_receipts_hidden_by_operating_unit_rule(self):
        r1 = self._make_ou_receipt()
        r2 = self._make_ou_receipt()

        approver = self.env["res.users"].create(
            {
                "name": "Restricted Approver",
                "login": "kmitl_restricted_approver",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref(
                                "receipt_kmitl.group_receipt_kmitl_remittance_approver"
                            ).id
                        ]
                    )
                ],
            }
        )
        approver.assigned_operating_unit_ids = self.ou

        remittance = self._make_remittance(receipts=r1 | r2)
        remittance.approver_id = approver
        remittance.action_submit()

        # Drift after submission (e.g. a later data correction): the record
        # rule now hides r2 from a non-sudo read by the approver, but
        # action_approve must still flip its state, not silently skip it.
        r2.sudo().operating_unit_id = self.ou_b

        remittance.with_user(approver).action_approve()
        self.assertEqual(remittance.state, "approved")
        self.assertEqual(r1.state, "approved")
        self.assertEqual(r2.state, "approved")

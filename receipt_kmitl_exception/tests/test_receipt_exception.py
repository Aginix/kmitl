# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptException(ReceiptKmitlCommon):
    """Exception rules are evaluated on every receipt create/edit (the receipt
    has no confirm step). Only blocking rules prevent saving."""

    def _receipt_vals(self, **overrides):
        vals = {
            "department_analytic_id": self.dept_a.id,
            "payment_method_id": self.pm_cash.id,
            "partner_id": self.walkin.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product_tuition.id,
                        "name": self.product_tuition.name,
                        "account_id": (
                            self.product_tuition.property_account_income_id.id
                        ),
                        "quantity": 1,
                        "price_unit": 5000.0,
                    },
                )
            ],
        }
        vals.update(overrides)
        return vals

    def _activate(self, xmlid):
        rule = self.env.ref("receipt_kmitl_exception.%s" % xmlid)
        rule.active = True
        return rule

    def _today(self):
        return fields.Date.context_today(self.env.user)

    def test_blocking_rule_blocks_backdated_create(self):
        self._activate("receipt_excep_backdated")
        past = self._today() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.env["kmitl.receipt"].create(self._receipt_vals(date=past))
            self.env.flush_all()

    def test_blocking_rule_allows_today_create(self):
        self._activate("receipt_excep_backdated")
        receipt = self.env["kmitl.receipt"].create(
            self._receipt_vals(date=self._today())
        )
        self.env.flush_all()
        self.assertTrue(receipt.exists())
        # number is minted at creation
        self.assertNotEqual(receipt.name, "/")

    def test_blocking_rule_blocks_on_edit(self):
        self._activate("receipt_excep_backdated")
        receipt = self.env["kmitl.receipt"].create(self._receipt_vals())
        past = self._today() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            receipt.write({"date": past})
            self.env.flush_all()

    def test_non_blocking_rule_does_not_block(self):
        rule = self._activate("receipt_excep_no_partner")
        receipt = self.env["kmitl.receipt"].create(
            self._receipt_vals(partner_id=False, is_walkin=False)
        )
        self.env.flush_all()
        self.assertTrue(receipt.exists())
        # detected and stored for visibility, but the save was allowed
        self.assertIn(rule, receipt.exception_ids)

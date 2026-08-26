# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestPayingAccountScreen(TransactionCase):
    """The หัวจ่าย screen has to be able to set what the rest of the module
    tells the officer to set there.

    Two error messages — the disbursement audit's "there is no cheque book to
    draw on" and the bank export's "the file would carry no sending account" —
    both end with *"Set it in Finance ▸ Settings ▸ Paying Accounts."* That
    sentence is only true while this action opens a form that carries the bank
    account, which it did not: ``accounting_kmitl`` ships a second, generic form
    for ``account.payment.method.line`` and neither view sets a priority, so the
    default lookup resolved the wrong one on its name alone.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.action = cls.env.ref("finance_kmitl.action_kmitl_paying_account")

    def test_the_action_opens_the_form_that_carries_the_bank_account(self):
        form = self.action.view_ids.filtered(
            lambda view: view.view_mode == "form"
        ).view_id
        self.assertEqual(
            form,
            self.env.ref("finance_kmitl.kmitl_paying_account_view_form"),
            "the Paying Accounts action must name its own form rather than "
            "leave Odoo to guess one",
        )
        arch = self.env["account.payment.method.line"].fields_view_get(
            view_id=form.id, view_type="form"
        )["arch"]
        self.assertIn("bank_account_id", arch)

    def test_every_seeded_paying_account_satisfies_the_new_domain(self):
        """``bank_account_id`` now offers only the institute's own accounts.

        A payee's account is where money goes, never where it comes from — but
        the install seeded these before the domain existed, so this is what says
        the two agree and no หัวจ่าย has been left pointing at something the
        dropdown would no longer offer.
        """
        accounts = self.env["account.payment.method.line"].search(
            safe_eval(self.action.domain)
        )
        self.assertTrue(accounts, "the install seeds paying accounts")
        banked = accounts.filtered("bank_account_id")
        self.assertTrue(banked)
        for line in banked:
            self.assertEqual(
                line.bank_account_id.partner_id,
                line.company_partner_id,
                "%s is booked against a bank account that is not the "
                "institute's own" % line.display_name,
            )

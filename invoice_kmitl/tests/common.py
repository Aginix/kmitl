# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, fields

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon


class InvoiceKmitlCommon(ReceiptKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # With the operating unit add-ons installed every document takes its unit from
        # the user, so the acting user needs one.
        cls.ou = False
        if "operating.unit" in cls.env:
            cls.ou = cls.env["operating.unit"].create(
                {
                    "name": "Invoice Test OU",
                    "code": "ITOU",
                    "partner_id": cls.company.partner_id.id,
                }
            )
            cls.env.user.write(
                {
                    "operating_unit_ids": [Command.link(cls.ou.id)],
                    "default_operating_unit_id": cls.ou.id,
                }
            )

        # --- A debtor with a receivable account of its own ---
        cls.receivable = cls.env["account.account"].create(
            {
                "code": "112101",
                "name": "Debtors",
                "account_type": "asset_receivable",
                "company_id": cls.company.id,
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Debtor", "property_account_receivable_id": cls.receivable.id}
        )

        # --- The AR journal the invoices are raised on, bound to this company ---
        journal = cls.env.ref("account_kmitl.journal_ar", raise_if_not_found=False)
        if not journal or journal.company_id != cls.company:
            journal = cls.env["account.journal"].create(
                {
                    "name": "Debtors",
                    "type": "sale",
                    "code": "ARK",
                    "default_account_id": cls.income_other.id,
                    "company_id": cls.company.id,
                }
            )
            xmlid = cls.env["ir.model.data"].search(
                [("module", "=", "account_kmitl"), ("name", "=", "journal_ar")]
            )
            if xmlid:
                xmlid.res_id = journal.id
                # The lookup is cached, and only unlink clears it.
                cls.env["ir.model.data"].clear_caches()
            else:
                cls.env["ir.model.data"].create(
                    {
                        "module": "account_kmitl",
                        "name": "journal_ar",
                        "model": "account.journal",
                        "res_id": journal.id,
                    }
                )
        cls.ar_journal = journal

        # --- The treasury office ---
        cls.treasury = cls.env["res.users"].create(
            {
                "name": "Treasury",
                "login": "kmitl_invoice_treasury",
                "groups_id": [
                    Command.set(
                        [cls.env.ref("invoice_kmitl.group_invoice_kmitl_approver").id]
                    )
                ],
            }
        )

    def _make_invoice(self, lines=None, **extra):
        today = fields.Date.context_today(self.env.user)
        lines = lines or [(self.product_tuition, 1, 5000.0)]
        vals = {
            "partner_id": self.customer.id,
            "date": today,
            "date_due": today + timedelta(days=30),
            "department_analytic_id": self.dept_a.id,
            "source_analytic_id": self.source_a.id,
            "fund_analytic_id": self.fund_a.id,
            "activity_analytic_id": self.activity_a.id,
            "line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "name": product.name,
                        "account_id": product.property_account_income_id.id,
                        "quantity": qty,
                        "price_unit": price,
                    }
                )
                for (product, qty, price) in lines
            ],
        }
        vals.update(extra)
        return self.env["kmitl.invoice"].create(vals)

    def _issue(self, invoices, **submission_vals):
        """Take the invoices through a submission, to the draft receivable entries."""
        vals = {
            "department_analytic_id": self.dept_a.id,
            "approver_id": self.treasury.id,
            "invoice_ids": [Command.set(invoices.ids)],
        }
        vals.update(submission_vals)
        submission = self.env["kmitl.invoice.submission"].create(vals)
        submission.action_submit()
        submission.action_accept()
        submission.action_done()
        return submission

    def _post(self, move):
        move._post(soft=False)
        return move

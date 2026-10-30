from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBeneficiaryUnits(TransactionCase):
    """A reservation owned by one unit may be made for several Beneficiary
    Units (budget ADR-0011 amendment): every one of them sees it, others do
    not, and naming another unit stays gated on the all-OU right."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        partner = env.company.partner_id
        cls.ou_owner, cls.ou_b, cls.ou_c, cls.ou_d = env["operating.unit"].create(
            [
                {"name": name, "code": code, "partner_id": partner.id}
                for name, code in (
                    ("Central", "BEN_A"),
                    ("Faculty B", "BEN_B"),
                    ("Faculty C", "BEN_C"),
                    ("Faculty D", "BEN_D"),
                )
            ]
        )
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-BEN",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.account = env["budget.account"].create(
            {"code": "BEN_ACC", "name": "Beneficiary", "budget_type": "expense"}
        )
        cls.users = {
            ou: env["res.users"].create(
                {
                    "name": "Budget user %s" % ou.code,
                    "login": "ben_user_%s" % ou.code.lower(),
                    "groups_id": [
                        Command.set([env.ref("budget.group_budget_user").id])
                    ],
                    "operating_unit_ids": [Command.set(ou.ids)],
                    "default_operating_unit_id": ou.id,
                }
            )
            for ou in (cls.ou_owner, cls.ou_b, cls.ou_c, cls.ou_d)
        }

    def _commitment_vals(self, owner, beneficiaries):
        return {
            "date": date.today(),
            "title": "Support",
            "account_id": self.account.id,
            "amount": 1000,
            "account_fiscal_year_id": self.fy.id,
            "company_id": self.env.company.id,
            "currency_id": self.env.company.currency_id.id,
            "operating_unit_id": owner.id,
            "beneficiary_operating_unit_ids": [Command.set(beneficiaries.ids)],
        }

    def test_every_beneficiary_unit_sees_the_reservation(self):
        commitment = self.env["budget.commitment"].create(
            self._commitment_vals(self.ou_owner, self.ou_b | self.ou_c)
        )
        for ou, visible in (
            (self.ou_owner, True),
            (self.ou_b, True),
            (self.ou_c, True),
            (self.ou_d, False),
        ):
            found = (
                self.env["budget.commitment"]
                .with_user(self.users[ou])
                .search([("id", "=", commitment.id)])
            )
            self.assertEqual(bool(found), visible, ou.code)

    def test_reserving_for_other_units_needs_all_ou_right(self):
        Commitment = self.env["budget.commitment"].with_user(self.users[self.ou_owner])
        # For its own unit only: unrestricted.
        Commitment.create(self._commitment_vals(self.ou_owner, self.ou_owner))
        with self.assertRaises(ValidationError):
            Commitment.create(
                self._commitment_vals(self.ou_owner, self.ou_owner | self.ou_b)
            )

    def test_beneficiary_names_readable_by_each_unit(self):
        """Unit B cannot read unit C, yet the form's read-only names list both."""
        commitment = self.env["budget.commitment"].create(
            self._commitment_vals(self.ou_owner, self.ou_b | self.ou_c)
        )
        as_b = commitment.with_user(self.users[self.ou_b])
        names = as_b.read(["beneficiary_operating_unit_names"])[0][
            "beneficiary_operating_unit_names"
        ]
        self.assertIn(self.ou_b.name, names)
        self.assertIn(self.ou_c.name, names)

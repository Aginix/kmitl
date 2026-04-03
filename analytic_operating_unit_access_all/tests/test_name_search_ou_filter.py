from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNameSearchOUFilter(TransactionCase):
    """Test _name_search OU filtering on account.analytic.account."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        OU = cls.env["operating.unit"]
        Account = cls.env["account.analytic.account"]
        Plan = cls.env["account.analytic.plan"]
        Users = cls.env["res.users"]

        cls.company = cls.env.company
        cls.ou_a = OU.create(
            {
                "name": "OU A",
                "code": "OUA",
                "partner_id": cls.company.partner_id.id,
                "company_id": cls.company.id,
            }
        )
        cls.ou_b = OU.create(
            {
                "name": "OU B",
                "code": "OUB",
                "partner_id": cls.company.partner_id.id,
                "company_id": cls.company.id,
            }
        )

        # Dedicated test plan to avoid limit issues with existing records
        cls.plan = Plan.create({"name": "Test OU Filter", "code": "test_ou_filter"})

        # Analytic accounts: one per OU, one shared (no OU)
        cls.acc_ou_a = Account.create(
            {
                "name": "Acc OU-A",
                "plan_id": cls.plan.id,
                "operating_unit_ids": [(4, cls.ou_a.id)],
            }
        )
        cls.acc_ou_b = Account.create(
            {
                "name": "Acc OU-B",
                "plan_id": cls.plan.id,
                "operating_unit_ids": [(4, cls.ou_b.id)],
            }
        )
        cls.acc_shared = Account.create(
            {
                "name": "Acc Shared",
                "plan_id": cls.plan.id,
                "operating_unit_ids": False,
            }
        )

        group_user = cls.env.ref("base.group_user")

        # User assigned to OU A only
        cls.user_a = Users.with_context(no_reset_password=True).create(
            {
                "name": "User A",
                "login": "test_ou_user_a",
                "password": "test_ou_user_a",
                "company_id": cls.company.id,
                "company_ids": [(4, cls.company.id)],
                "operating_unit_ids": [(4, cls.ou_a.id)],
                "groups_id": [(6, 0, [group_user.id])],
            }
        )

        # User with "Access all OUs' analytics" group
        group_all_ou = cls.env.ref(
            "analytic_operating_unit_access_all.group_all_ou_analytic"
        )
        cls.user_all = Users.with_context(no_reset_password=True).create(
            {
                "name": "User All OU",
                "login": "test_ou_user_all",
                "password": "test_ou_user_all",
                "company_id": cls.company.id,
                "company_ids": [(4, cls.company.id)],
                "operating_unit_ids": [(4, cls.ou_a.id)],
                "groups_id": [(6, 0, [group_user.id, group_all_ou.id])],
            }
        )

    def _name_search_ids(self, user=None, context=None):
        """Return ids from name_search as the given user."""
        env = self.env
        if user:
            env = env(user=user)
        if context:
            env = env(context=dict(env.context, **context))
        results = env["account.analytic.account"].name_search(
            "", args=[("plan_id", "=", self.plan.id)]
        )
        return [r[0] for r in results]

    # ------------------------------------------------------------------
    # Default: filter by user's OU
    # ------------------------------------------------------------------

    def test_user_sees_own_ou_and_shared(self):
        """Regular user sees only their OU's accounts + shared accounts."""
        ids = self._name_search_ids(user=self.user_a)
        self.assertIn(self.acc_ou_a.id, ids)
        self.assertIn(self.acc_shared.id, ids)
        self.assertNotIn(self.acc_ou_b.id, ids)

    # ------------------------------------------------------------------
    # Bypass: group "Access all OUs' analytics"
    # ------------------------------------------------------------------

    def test_group_bypass_sees_all(self):
        """User with group_all_ou_analytic sees all accounts."""
        ids = self._name_search_ids(user=self.user_all)
        self.assertIn(self.acc_ou_a.id, ids)
        self.assertIn(self.acc_ou_b.id, ids)
        self.assertIn(self.acc_shared.id, ids)

    # ------------------------------------------------------------------
    # Bypass: context key all_analytic_ou
    # ------------------------------------------------------------------

    def test_context_bypass_sees_all(self):
        """Regular user with context all_analytic_ou=True sees all accounts."""
        ids = self._name_search_ids(
            user=self.user_a, context={"all_analytic_ou": True}
        )
        self.assertIn(self.acc_ou_a.id, ids)
        self.assertIn(self.acc_ou_b.id, ids)
        self.assertIn(self.acc_shared.id, ids)


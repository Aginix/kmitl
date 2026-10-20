from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKmitlProjectPoolTag(TransactionCase):
    def test_pool_tag_registered(self):
        fields = [tag["field"] for tag in self.env["budget.dashboard"].get_pool_tags()]
        self.assertIn("kmitl_project_analytic_id", fields)

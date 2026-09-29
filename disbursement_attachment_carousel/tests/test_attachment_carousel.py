# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttachmentCarouselAction(TransactionCase):
    """The action_open_attachment_carousel returns an ir.actions.client dict
    that the OWL registry entry `disbursement_attachment_carousel` renders as
    a dialog. Only the shape of the dict is checked here; the OWL behaviour
    (prev/next, thumbnails, keyboard) is exercised by hand in the browser."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        AAA = cls.env["account.analytic.account"]
        cls.dept = AAA.create({
            "name": "Dept",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_departments").id,
        })
        cls.source = AAA.create({
            "name": "Gov",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_sources").id,
        })
        cls.fund = AAA.create({
            "name": "Fund",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_funds").id,
        })
        cls.activity = AAA.create({
            "name": "Act",
            "plan_id": cls.env.ref(
                "account_analytic_kmitl.analytic_plan_activities").id,
        })
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Svc", "type": "service"}
        )

    def _make_request(self):
        dr = self.env["disbursement.request"].create({
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "name": "line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "partner_id": self.partner.id,
            })],
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        return dr

    def test_action_returns_client_action_dialog(self):
        dr = self._make_request()
        action = dr.action_open_attachment_carousel()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "disbursement_attachment_carousel")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["params"]["res_id"], dr.id)
        self.assertIn("dialog_size", action["context"])

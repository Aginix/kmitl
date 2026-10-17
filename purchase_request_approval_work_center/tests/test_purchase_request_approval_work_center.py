from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestApprovalWorkCenter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        area = cls.env.ref("purchase_request_work_center.work_center_area_procurement")
        partner = cls.env.company.partner_id
        cls.ou = cls.env["operating.unit"].create(
            {"name": "WC PA OU", "code": "WCPA", "partner_id": partner.id}
        )
        plan = cls.env["account.analytic.plan"].create({"name": "WC PA Departments"})
        cls.dept = cls.env["account.analytic.account"].create(
            {"name": "ภาควิชาไฟฟ้า (PA test)", "plan_id": plan.id}
        )
        cls.wc_dept = cls.env["work.center"].create(
            {
                "name": "ศูนย์งานภาคไฟฟ้า (PA)",
                "area_id": area.id,
                "operating_unit_id": cls.ou.id,
            }
        )
        # A PA can be routed to the same work center as its พ.1.
        for model in ("purchase.request", "purchase.request.approval"):
            cls.env["work.center.rule"].create(
                {
                    "work_center_id": cls.wc_dept.id,
                    "model_id": cls.env["ir.model"]._get(model).id,
                    "domain": repr([("requesting_department_id", "=", cls.dept.id)]),
                }
            )

    def test_pr_and_pa_share_work_center(self):
        pr = self.env["purchase.request"].create(
            {
                "title": "Test PR",
                "requested_by": self.env.ref("base.user_admin").id,
                "requesting_department_id": self.dept.id,
                "operating_unit_id": self.ou.id,
            }
        )
        pa = self.env["purchase.request.approval"].create(
            {
                "request_id": pr.id,
                "title": "Test PA",
                "requesting_department_id": self.dept.id,
                "operating_unit_id": self.ou.id,
            }
        )
        self.assertEqual(pr.work_center_id, self.wc_dept)
        self.assertEqual(pa.work_center_id, self.wc_dept)

    def test_work_center_writable_under_validation(self):
        PA = self.env["purchase.request.approval"]
        self.assertIn("work_center_id", PA._get_under_validation_exceptions())
        self.assertIn("work_center_id", PA._get_after_validation_exceptions())

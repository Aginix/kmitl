from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestWorkCenter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.area = cls.env.ref(
            "purchase_request_work_center.work_center_area_procurement"
        )
        cls.pr_model = cls.env["ir.model"]._get("purchase.request")
        partner = cls.env.company.partner_id
        OU = cls.env["operating.unit"]
        cls.ou_a = OU.create(
            {"name": "WC OU A", "code": "WCPRA", "partner_id": partner.id}
        )
        cls.ou_b = OU.create(
            {"name": "WC OU B", "code": "WCPRB", "partner_id": partner.id}
        )
        plan = cls.env["account.analytic.plan"].create({"name": "WC Test Departments"})
        Analytic = cls.env["account.analytic.account"]
        cls.dept = Analytic.create({"name": "ภาควิชาไฟฟ้า (test)", "plan_id": plan.id})
        cls.other_dept = Analytic.create(
            {"name": "ภาควิชาโยธา (test)", "plan_id": plan.id}
        )

        WorkCenter = cls.env["work.center"]
        cls.wc_dept = WorkCenter.create(
            {
                "name": "ศูนย์งานภาคไฟฟ้า",
                "area_id": cls.area.id,
                "operating_unit_id": cls.ou_a.id,
            }
        )
        cls.wc_central = WorkCenter.create(
            {"name": "ศูนย์งานพัสดุกลาง", "area_id": cls.area.id}
        )
        Rule = cls.env["work.center.rule"]
        Rule.create(
            {
                "work_center_id": cls.wc_dept.id,
                "model_id": cls.pr_model.id,
                "domain": repr([("requesting_department_id", "=", cls.dept.id)]),
                "sequence": 1,
            }
        )
        Rule.create(
            {
                "work_center_id": cls.wc_central.id,
                "model_id": cls.pr_model.id,
                "domain": repr([("requesting_department_id", "=", cls.other_dept.id)]),
                "sequence": 2,
            }
        )

    def _pr(self, department, ou):
        return self.env["purchase.request"].create(
            {
                "title": "Test PR",
                "requested_by": self.env.ref("base.user_admin").id,
                "requesting_department_id": department.id,
                "operating_unit_id": ou.id,
            }
        )

    def test_draft_routed_then_sticky(self):
        pr = self._pr(self.dept, self.ou_a)
        self.assertEqual(pr.work_center_id, self.wc_dept)
        pr.requesting_department_id = self.other_dept
        self.assertEqual(pr.work_center_id, self.wc_central)
        pr.state = "to_verify"
        pr.requesting_department_id = self.dept
        self.assertEqual(pr.work_center_id, self.wc_central)

    def test_unit_level_rule_respects_ou(self):
        self.assertFalse(self._pr(self.dept, self.ou_b).work_center_id)

    def test_central_counter_counts_viewer_ou_only(self):
        self._pr(self.other_dept, self.ou_a)
        self._pr(self.other_dept, self.ou_b)
        counter = self.env.ref("purchase_request_work_center.counter_pr_draft")
        user = self.env["res.users"].create(
            {
                "name": "ธุรการ OU A",
                "login": "wc_pr_clerk_a",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "purchase_request.group_purchase_request_user"
                            ).id,
                        ],
                    )
                ],
                "operating_unit_ids": [(6, 0, self.ou_a.ids)],
                "default_operating_unit_id": self.ou_a.id,
            }
        )

        def count(wc):
            return next(c["count"] for c in wc.counter_data if c["id"] == counter.id)

        self.assertEqual(count(self.wc_central), 2)
        self.assertEqual(count(self.wc_central.with_user(user)), 1)

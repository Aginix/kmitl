from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


class WorkCenterTestDoc(models.Model):
    """Throwaway document carrying the work center mixin."""

    _name = "test.work.center.doc"
    _description = "Test Work Center Document"
    _inherit = ["mail.thread", "work.center.mixin"]

    name = fields.Char()
    state = fields.Selection([("draft", "Draft"), ("done", "Done")], default="draft")
    operating_unit_id = fields.Many2one("operating.unit")
    partner_id = fields.Many2one("res.partner")

    @api.model
    def _work_center_routing_fields(self):
        return super()._work_center_routing_fields() + ["partner_id"]


@tagged("post_install", "-at_install")
class TestWorkCenter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        WorkCenterTestDoc._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr, ["test.work.center.doc"], {"module": "work_center"}
        )
        cls.Doc = cls.env["test.work.center.doc"]
        cls.WorkCenter = cls.env["work.center"]
        cls.Rule = cls.env["work.center.rule"]
        cls.doc_model = cls.env["ir.model"]._get("test.work.center.doc")

        cls.area = cls.env["work.center.area"].create(
            {
                "name": "Test Area",
                "code": "test_area",
                "model_ids": [(6, 0, cls.doc_model.ids)],
            }
        )
        partner_company = cls.env.company.partner_id
        cls.ou_a = cls.env["operating.unit"].create(
            {"name": "OU A", "code": "WC-A", "partner_id": partner_company.id}
        )
        cls.ou_b = cls.env["operating.unit"].create(
            {"name": "OU B", "code": "WC-B", "partner_id": partner_company.id}
        )
        Partner = cls.env["res.partner"]
        cls.dept = Partner.create({"name": "ภาควิชาไฟฟ้า", "is_company": True})
        cls.sub_dept = Partner.create({"name": "สาขา", "parent_id": cls.dept.id})
        cls.other_dept = Partner.create({"name": "ภาควิชาโยธา", "is_company": True})

        cls.wc_dept = cls.WorkCenter.create(
            {
                "name": "ศูนย์งานภาคไฟฟ้า",
                "area_id": cls.area.id,
                "operating_unit_id": cls.ou_a.id,
            }
        )
        cls.wc_other = cls.WorkCenter.create(
            {
                "name": "ศูนย์งานภาคโยธา",
                "area_id": cls.area.id,
                "operating_unit_id": cls.ou_a.id,
            }
        )
        cls.wc_central = cls.WorkCenter.create(
            {"name": "ศูนย์งานกลาง", "area_id": cls.area.id}
        )
        cls.rule_dept = cls._rule(
            cls.wc_dept, [("partner_id", "child_of", cls.dept.id)]
        )
        cls.rule_other = cls._rule(
            cls.wc_other, [("partner_id", "=", cls.other_dept.id)], sequence=20
        )

    @classmethod
    def _rule(cls, work_center, domain, sequence=10):
        return cls.Rule.create(
            {
                "work_center_id": work_center.id,
                "model_id": cls.doc_model.id,
                "domain": repr(domain),
                "sequence": sequence,
            }
        )

    def _doc(self, **vals):
        vals.setdefault("operating_unit_id", self.ou_a.id)
        return self.Doc.create(vals)

    # ------------------------------------------------------------------
    # Area
    # ------------------------------------------------------------------
    def test_area_gets_one_unassigned_card(self):
        unassigned = self.WorkCenter.search(
            [("area_id", "=", self.area.id), ("is_unassigned", "=", True)]
        )
        self.assertEqual(len(unassigned), 1)
        self.assertEqual(self.area.unassigned_work_center_id, unassigned)
        self.assertFalse(unassigned.operating_unit_id)
        with self.assertRaises(UserError):
            unassigned.unlink()

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def test_routed_on_create(self):
        self.assertEqual(
            self._doc(partner_id=self.dept.id).work_center_id, self.wc_dept
        )

    def test_child_of_matches_sub_unit(self):
        self.assertEqual(
            self._doc(partner_id=self.sub_dept.id).work_center_id, self.wc_dept
        )

    def test_child_of_in_memory_preview(self):
        doc = self.Doc.new(
            {
                "state": "draft",
                "partner_id": self.sub_dept.id,
                "operating_unit_id": self.ou_a.id,
            }
        )
        self.assertEqual(doc.work_center_id, self.wc_dept)

    def test_draft_follows_rules(self):
        doc = self._doc(partner_id=self.dept.id)
        doc.partner_id = self.other_dept
        self.assertEqual(doc.work_center_id, self.wc_other)

    def test_sticky_after_draft(self):
        doc = self._doc(partner_id=self.dept.id)
        doc.state = "done"
        doc.partner_id = self.other_dept
        self.assertEqual(doc.work_center_id, self.wc_dept)

    def test_manual_edit_after_draft_kept(self):
        doc = self._doc(partner_id=self.dept.id)
        doc.state = "done"
        doc.work_center_id = self.wc_central
        self.assertEqual(doc.work_center_id, self.wc_central)

    def test_manual_pick_in_draft_pins(self):
        doc = self._doc(partner_id=self.dept.id)
        doc.work_center_id = self.wc_central
        self.assertTrue(doc.work_center_manual)
        doc.partner_id = self.other_dept
        self.assertEqual(doc.work_center_id, self.wc_central)
        # Clearing un-pins and routes by the rules again.
        doc.work_center_id = False
        self.assertFalse(doc.work_center_manual)
        self.assertEqual(doc.work_center_id, self.wc_other)

    def test_writing_rule_result_does_not_pin(self):
        doc = self._doc(partner_id=self.dept.id, work_center_id=self.wc_dept.id)
        self.assertFalse(doc.work_center_manual)
        doc.partner_id = self.other_dept
        self.assertEqual(doc.work_center_id, self.wc_other)

    def test_clear_after_draft_stays_empty(self):
        doc = self._doc(partner_id=self.dept.id)
        doc.state = "done"
        doc.work_center_id = False
        self.assertFalse(doc.work_center_id)

    def test_ou_guard(self):
        doc = self._doc(partner_id=self.dept.id, operating_unit_id=self.ou_b.id)
        self.assertFalse(doc.work_center_id)

    def test_central_matches_any_ou(self):
        self._rule(self.wc_central, [("partner_id", "=", False)], sequence=99)
        doc = self._doc(operating_unit_id=self.ou_b.id)
        self.assertEqual(doc.work_center_id, self.wc_central)

    def test_no_match(self):
        self.assertFalse(self._doc().work_center_id)

    def test_sequence_priority(self):
        self._rule(self.wc_central, [("partner_id", "child_of", self.dept.id)], 1)
        self.assertEqual(
            self._doc(partner_id=self.dept.id).work_center_id, self.wc_central
        )

    def test_archived_work_center_ignored(self):
        self.wc_dept.active = False
        self.assertFalse(self._doc(partner_id=self.dept.id).work_center_id)

    def test_unassigned_card_not_assignable(self):
        doc = self._doc()
        with self.assertRaises(ValidationError):
            doc.work_center_id = self.area.unassigned_work_center_id

    def test_rule_cannot_target_unassigned(self):
        with self.assertRaises(ValidationError):
            self._rule(self.area.unassigned_work_center_id, [])

    def test_rule_invalid_domain(self):
        with self.assertRaises(ValidationError):
            self._rule(self.wc_central, [("no_such_field", "=", 1)])

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    def _counter(self, domain):
        return self.env["work.center.counter"].create(
            {
                "name": "Draft",
                "area_id": self.area.id,
                "model_id": self.doc_model.id,
                "domain": repr(domain),
            }
        )

    @staticmethod
    def _count(work_center, counter):
        return next(
            c["count"] for c in work_center.counter_data if c["id"] == counter.id
        )

    def test_counters(self):
        counter = self._counter([("state", "=", "draft")])
        self._doc(partner_id=self.dept.id)
        self._doc(partner_id=self.sub_dept.id)
        self._doc(partner_id=self.dept.id, state="done")
        self._doc()
        self.assertEqual(self._count(self.wc_dept, counter), 2)
        self.assertEqual(self._count(self.wc_other, counter), 0)
        self.assertEqual(self._count(self.area.unassigned_work_center_id, counter), 1)
        action = self.wc_dept.with_context(
            work_center_counter_id=counter.id
        ).action_open_counter()
        self.assertEqual(self.Doc.search_count(action["domain"]), 2)

    def test_counter_skipped_without_read_access(self):
        self._counter([])
        user = self.env["res.users"].create(
            {
                "name": "No Access",
                "login": "wc_no_access",
                "groups_id": [(6, 0, self.env.ref("base.group_user").ids)],
                "operating_unit_ids": [(6, 0, self.ou_a.ids)],
            }
        )
        self.assertEqual(self.wc_dept.with_user(user).counter_data, [])

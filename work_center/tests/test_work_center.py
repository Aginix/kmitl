from odoo import _lt, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


class WorkCenterTestDoc(models.Model):
    """Throwaway document carrying the station mixin."""

    _name = "test.work.center.doc"
    _description = "Test Work Center Document"
    _inherit = ["mail.thread", "mail.activity.mixin", "work.center.mixin"]

    name = fields.Char()
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"), ("done", "Done")],
        default="draft",
    )
    operating_unit_id = fields.Many2one("operating.unit")
    partner_id = fields.Many2one("res.partner")

    @api.model
    def _work_center_acts(self):
        # Existing groups only: a group created in setUpClass has no xmlid for
        # the declaration to point at.
        return super()._work_center_acts() + [
            {
                "code": "test.check",
                "name": _lt("Check"),
                "kind": "act",
                "group": "base.group_partner_manager",
                "sequence": 10,
                "module": "work_center",
            },
            {
                "code": "test.approve",
                "name": _lt("Approve"),
                "kind": "act",
                "group": "base.group_erp_manager",
                "sequence": 20,
                "module": "work_center",
            },
            {
                "code": "test.nobody",
                "name": _lt("Act nobody may do"),
                "kind": "act",
                "sequence": 30,
                "module": "work_center",
            },
            {
                "code": "test.edit_header",
                "name": _lt("Edit the header"),
                "kind": "edit",
                "group": "base.group_partner_manager",
                "sequence": 40,
                "module": "work_center",
            },
        ]

    @api.model
    def _work_center_circuit_domain(self):
        return [("state", "=", "in_progress")]

    def _work_center_on_exit(self):
        self.state = "done"

    def _work_center_on_send_back(self, reason):
        self.state = "draft"


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
        # The test model has no access rights of its own: a dedicated group
        # gets them, so a plain internal user still has none (see
        # test_counter_skipped_without_read_access).
        cls.test_group = cls.env["res.groups"].create({"name": "Station test access"})
        cls.env["ir.model.access"].create(
            {
                "name": "test.work.center.doc test group",
                "model_id": cls.doc_model.id,
                "group_id": cls.test_group.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
        )
        # The registry hook ran before the test model existed.
        cls.env["work.center.act"]._reflect_acts()
        Act = cls.env["work.center.act"]
        cls.act_check = Act.search([("code", "=", "test.check")])
        cls.act_approve = Act.search([("code", "=", "test.approve")])
        cls.act_nobody = Act.search([("code", "=", "test.nobody")])
        cls.edit_header = Act.search([("code", "=", "test.edit_header")])

        cls.area = cls.env["work.center.area"].create(
            {
                "name": "Test Area",
                "code": "test_area",
                "model_ids": [(6, 0, cls.doc_model.ids)],
            }
        )
        cls.other_area = cls.env["work.center.area"].create(
            {"name": "Other Area", "code": "test_area_other"}
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

        # Two users holding the check role, one the approve role, one neither.
        Users = cls.env["res.users"].with_context(no_reset_password=True)

        def _user(login, *groups):
            return Users.create(
                {
                    "name": login,
                    "login": login,
                    "groups_id": [
                        (4, g.id)
                        for g in (cls.env.ref("base.group_user"), cls.test_group)
                        + groups
                    ],
                    "operating_unit_ids": [(6, 0, cls.ou_a.ids)],
                }
            )

        group_check = cls.env.ref("base.group_partner_manager")
        cls.user_a = _user("wc_user_a", group_check)
        cls.user_a2 = _user("wc_user_a2", group_check)
        cls.user_b = _user("wc_user_b", cls.env.ref("base.group_erp_manager"))
        cls.user_none = _user("wc_user_none")
        cls.user_manager = _user(
            "wc_user_manager", cls.env.ref("work_center.group_work_center_manager")
        )

        cls.wc_dept = cls.WorkCenter.create(
            {
                "name": "สถานีภาคไฟฟ้า",
                "area_id": cls.area.id,
                "operating_unit_id": cls.ou_a.id,
                "member_ids": [(6, 0, cls.user_a.ids)],
                "allowed_act_ids": [(6, 0, (cls.act_check | cls.act_nobody).ids)],
                "required_act_ids": [(6, 0, cls.act_check.ids)],
                "allowed_edit_ids": [(6, 0, cls.edit_header.ids)],
            }
        )
        cls.wc_other = cls.WorkCenter.create(
            {
                "name": "สถานีภาคโยธา",
                "area_id": cls.area.id,
                "operating_unit_id": cls.ou_a.id,
                "allowed_act_ids": [(6, 0, cls.act_check.ids)],
            }
        )
        cls.wc_central = cls.WorkCenter.create(
            {
                "name": "สถานีกลาง",
                "area_id": cls.area.id,
                "allowed_act_ids": [(6, 0, cls.act_approve.ids)],
                "required_act_ids": [(6, 0, cls.act_approve.ids)],
            }
        )
        # Off the route: a side trip for a diverted document.
        cls.wc_side = cls.WorkCenter.create(
            {
                "name": "สถานีข้างทาง",
                "area_id": cls.area.id,
                "allowed_act_ids": [(6, 0, cls.act_check.ids)],
            }
        )
        cls.wc_foreign = cls.WorkCenter.create(
            {
                "name": "สถานีต่างระบบงาน",
                "area_id": cls.other_area.id,
                "member_ids": [(6, 0, cls.user_a.ids)],
            }
        )
        cls.route = cls.env["work.center.route"].create(
            {
                "name": "Test Route",
                "area_id": cls.area.id,
                "model_id": cls.doc_model.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Check",
                            "sequence": 10,
                            "work_center_ids": [
                                (6, 0, (cls.wc_dept | cls.wc_other).ids)
                            ],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Approve",
                            "sequence": 20,
                            "work_center_ids": [(6, 0, cls.wc_central.ids)],
                        },
                    ),
                ],
            }
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

    def _enter(self, **vals):
        """A document that has entered the circuit at line 1 of the route."""
        doc = self._doc(**vals)
        doc.state = "in_progress"
        doc._work_center_enter()
        return doc

    def _central_candidate(self, domain, sequence=10):
        """A second central station on line 1, chosen by its own rule."""
        station = self.WorkCenter.create(
            {
                "name": "สถานีกลางเสริม",
                "area_id": self.area.id,
                "allowed_act_ids": [(6, 0, self.act_check.ids)],
            }
        )
        self.route.line_ids[0].work_center_ids = [(4, station.id)]
        self._rule(station, domain, sequence)
        return station

    def _arrival_todos(self, doc):
        arrival = self.env.ref("work_center.mail_activity_station_arrival")
        return doc.activity_ids.filtered(lambda a: a.activity_type_id == arrival)

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
    # Entering the circuit
    # ------------------------------------------------------------------
    def test_routed_on_create(self):
        doc = self._enter(partner_id=self.dept.id)
        self.assertEqual(doc.work_center_id, self.wc_dept)
        self.assertEqual(len(doc.work_center_visit_ids), 1)
        self.assertEqual(doc.work_center_visit_ids.arrival_act, "enter")
        self.assertFalse(doc.work_center_visit_ids.departure_date)

    def test_child_of_matches_sub_unit(self):
        self.assertEqual(
            self._enter(partner_id=self.sub_dept.id).work_center_id, self.wc_dept
        )

    # ------------------------------------------------------------------
    # Moving along the route
    # ------------------------------------------------------------------
    def test_forward_moves_to_next_line_and_exit_calls_hook(self):
        doc = self._enter(partner_id=self.dept.id)
        doc._work_center_act_done("test.check")
        doc._work_center_forward()
        self.assertEqual(doc.work_center_id, self.wc_central)
        first = doc.work_center_visit_ids.filtered(
            lambda v: v.work_center_id == self.wc_dept
        )
        self.assertEqual(first.departure_act, "forward")
        doc._work_center_act_done("test.approve")
        doc._work_center_forward()
        self.assertFalse(doc.work_center_id)
        self.assertEqual(doc.state, "done")
        last = doc._work_center_last_visit()
        self.assertEqual(last.work_center_id, self.wc_central)
        self.assertEqual(last.departure_act, "exit")
        self.assertFalse(doc._work_center_open_visit())

    def test_divert_then_forward_rejoins_after_last_on_route_visit(self):
        doc = self._enter(partner_id=self.dept.id)
        doc._work_center_act_done("test.check")
        doc._work_center_forward()
        # Back to line 1 at the other station: "next" is read from the log.
        doc._work_center_divert(self.wc_other, "another look")
        self.assertEqual(doc.work_center_id, self.wc_other)
        self.assertEqual(doc._work_center_open_visit().arrival_act, "divert")
        self.assertEqual(doc.work_center_next_id, self.wc_central)
        # A side trip off the route rejoins after the last on-route station.
        doc._work_center_divert(self.wc_side, "side trip")
        self.assertEqual(doc.work_center_next_id, self.wc_central)
        doc._work_center_forward()
        self.assertEqual(doc.work_center_id, self.wc_central)

    def test_divert_to_another_area_refused(self):
        doc = self._enter(partner_id=self.dept.id)
        with self.assertRaises(UserError):
            doc._work_center_divert(self.wc_foreign, "wrong desk")
        with self.assertRaises(UserError):
            doc._work_center_divert(self.wc_other, "  ")
        self.assertEqual(doc.work_center_id, self.wc_dept)

    def test_missing_required_act_needs_reason(self):
        doc = self._enter(partner_id=self.dept.id)
        self.assertEqual(doc.work_center_missing_act_ids, self.act_check)
        with self.assertRaises(UserError):
            doc._work_center_forward()
        with self.assertRaises(UserError):
            doc._work_center_forward("   ")
        doc._work_center_forward("checked on paper")
        visit = doc.work_center_visit_ids.filtered(
            lambda v: v.work_center_id == self.wc_dept
        )
        self.assertEqual(visit.departure_reason, "checked on paper")
        self.assertEqual(visit.skipped_act_ids, self.act_check)

    def test_send_back_and_cancel_close_visit_todos_and_pointer(self):
        doc = self._enter(partner_id=self.dept.id)
        self.assertEqual(self._arrival_todos(doc).user_id, self.user_a)
        doc._work_center_send_back("wrong payee")
        self.assertFalse(doc.work_center_id)
        self.assertEqual(doc.state, "draft")
        self.assertFalse(self._arrival_todos(doc))
        self.assertFalse(doc._work_center_open_visit())
        visit = doc.work_center_visit_ids
        self.assertEqual(visit.departure_act, "send_back")
        self.assertEqual(visit.departure_reason, "wrong payee")
        cancelled = self._enter(partner_id=self.dept.id)
        cancelled._work_center_leave("cancel")
        self.assertFalse(cancelled.work_center_id)
        self.assertFalse(self._arrival_todos(cancelled))
        self.assertEqual(cancelled.work_center_visit_ids.departure_act, "cancel")
        # Leaving twice is a no-op.
        cancelled._work_center_leave("cancel")
        self.assertEqual(len(cancelled.work_center_visit_ids), 1)

    def test_visit_is_append_only(self):
        doc = self._enter(partner_id=self.dept.id)
        visit = doc._work_center_open_visit()
        with self.assertRaises(UserError):
            visit.write({"departure_reason": "tampered"})
        with self.assertRaises(UserError):
            visit.with_context(work_center_moving=True).write(
                {"work_center_id": self.wc_other.id}
            )
        with self.assertRaises(UserError):
            visit.unlink()
        doc._work_center_leave("cancel")
        with self.assertRaises(UserError):
            visit.with_context(work_center_moving=True).write(
                {"departure_reason": "late"}
            )

    def test_membership_narrows_and_snapshot_freezes(self):
        doc = self._enter(partner_id=self.dept.id)  # members: user_a
        visit = doc._work_center_open_visit()
        self.assertEqual(visit.responsible_user_ids, self.user_a)
        self.assertEqual(visit.responsible_source, "members")
        self.env.invalidate_all()
        # The role alone is not enough where the station has members.
        with self.assertRaises(AccessError):
            doc.with_user(self.user_a2)._work_center_check_act("test.check")
        self.assertFalse(doc.with_user(self.user_a2)._work_center_offers("test.check"))
        # The member holding the role may.
        doc.with_user(self.user_a)._work_center_check_act("test.check")
        self.assertTrue(doc.with_user(self.user_a)._work_center_offers("test.check"))
        # An act the station does not list is refused, even under su.
        with self.assertRaises(UserError):
            doc._work_center_check_act("test.approve")
        # A member without the role is refused; so is an act without a role.
        self.wc_dept.member_ids = [(4, self.user_none.id)]
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            doc.with_user(self.user_none)._work_center_check_act("test.check")
        with self.assertRaises(AccessError):
            doc.with_user(self.user_a)._work_center_check_act("test.nobody")
        # The snapshot survives a membership change.
        self.wc_dept.member_ids = [(6, 0, self.user_a2.ids)]
        self.assertEqual(visit.responsible_user_ids, self.user_a)
        # Only the people responsible move the document.
        self.env.invalidate_all()
        self.assertFalse(doc.with_user(self.user_a).work_center_can_move)
        self.assertTrue(doc.with_user(self.user_a2).work_center_can_move)
        with self.assertRaises(AccessError):
            doc.with_user(self.user_a)._work_center_divert(self.wc_other, "no")
        # A memberless station snapshots the role holders (the admin is seated
        # in the group too, hence assertIn).
        other = self._enter(partner_id=self.other_dept.id)
        snapshot = other._work_center_open_visit()
        self.assertEqual(snapshot.responsible_source, "role")
        self.assertIn(self.user_a, snapshot.responsible_user_ids)
        self.assertIn(self.user_a2, snapshot.responsible_user_ids)
        self.assertNotIn(self.user_none, snapshot.responsible_user_ids)

    def test_resubmit_enters_line_one_regardless_of_history(self):
        doc = self._enter(partner_id=self.dept.id)
        doc._work_center_act_done("test.check")
        doc._work_center_forward()
        self.assertEqual(doc.work_center_id, self.wc_central)
        doc._work_center_send_back("fix and resend")
        doc.state = "in_progress"
        doc._work_center_enter("resubmit")
        self.assertEqual(doc.work_center_id, self.wc_dept)
        self.assertEqual(doc._work_center_open_visit().arrival_act, "resubmit")

    # ------------------------------------------------------------------
    # Placement rules
    # ------------------------------------------------------------------
    def test_ou_guard(self):
        doc = self._enter(partner_id=self.dept.id, operating_unit_id=self.ou_b.id)
        self.assertFalse(doc.work_center_id)
        self.assertEqual(
            doc._work_center_open_visit().work_center_id,
            self.area.unassigned_work_center_id,
        )

    def test_central_matches_any_ou(self):
        central = self._central_candidate([("partner_id", "=", False)], sequence=99)
        # Alone among the candidates of its operating unit.
        self.assertEqual(
            self._enter(operating_unit_id=self.ou_b.id).work_center_id, central
        )
        # Chosen by its rule among stations of the same operating unit.
        self.assertEqual(self._enter().work_center_id, central)

    def test_no_match(self):
        doc = self._enter()
        card = self.area.unassigned_work_center_id
        self.assertFalse(doc.work_center_id)
        visit = doc._work_center_open_visit()
        self.assertEqual(visit.work_center_id, card)
        self.assertEqual(visit.responsible_source, "fallback")
        # Only a station administrator frees it, by diverting it to a station.
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            doc.with_user(self.user_a)._work_center_divert(self.wc_other, "place it")
        with self.assertRaises(UserError):
            doc._work_center_forward()
        doc.with_user(self.user_manager)._work_center_divert(
            self.wc_other, "placed by hand"
        )
        self.assertEqual(doc.work_center_id, self.wc_other)

    def test_sequence_priority(self):
        central = self._central_candidate(
            [("partner_id", "child_of", self.dept.id)], sequence=1
        )
        self.assertEqual(self._enter(partner_id=self.dept.id).work_center_id, central)

    def test_archived_work_center_ignored(self):
        self.wc_dept.active = False
        self.assertEqual(
            self._enter(partner_id=self.dept.id).work_center_id, self.wc_other
        )

    def test_unassigned_card_not_assignable(self):
        doc = self._doc()
        card = self.area.unassigned_work_center_id
        with self.assertRaises(UserError):
            doc.work_center_id = card
        with self.assertRaises(ValidationError):
            doc.with_context(work_center_moving=True).work_center_id = card

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
                "name": "Waiting",
                "area_id": self.area.id,
                "model_id": self.doc_model.id,
                "domain": repr(domain),
            }
        )

    @staticmethod
    def _count(work_center, counter):
        # A Json field stores an empty list as False.
        return next(
            c["count"]
            for c in (work_center.counter_data or [])
            if c["id"] == counter.id
        )

    def test_counters(self):
        counter = self._counter([])
        self._enter(partner_id=self.dept.id)
        self._enter(partner_id=self.sub_dept.id)
        # Out of the circuit again: held by no station, counted nowhere.
        self._enter(partner_id=self.dept.id)._work_center_send_back("not ready")
        self._doc()  # a draft that never entered
        self._enter()  # no rule matched: waits on the Unassigned card
        self.assertEqual(self._count(self.wc_dept, counter), 2)
        self.assertEqual(self._count(self.wc_other, counter), 0)
        self.assertEqual(self._count(self.area.unassigned_work_center_id, counter), 1)
        action = self.wc_dept.with_context(
            work_center_counter_id=counter.id
        ).action_open_counter()
        self.assertEqual(self.Doc.search_count(action["domain"]), 2)
        action = self.area.unassigned_work_center_id.with_context(
            work_center_counter_id=counter.id
        ).action_open_counter()
        self.assertEqual(self.Doc.search_count(action["domain"]), 1)

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
        self.assertFalse(self.wc_dept.with_user(user).counter_data)

    def test_counter_data_empty_without_counters(self):
        """A Json field keeps an empty list as False; the kanban guards for it."""
        self.assertFalse(self.wc_dept.counter_data)

    # ------------------------------------------------------------------
    # Area
    # ------------------------------------------------------------------
    def test_unassigned_card_has_no_company(self):
        self.assertFalse(self.area.unassigned_work_center_id.company_id)

    def test_model_belongs_to_one_area_only(self):
        with self.assertRaises(ValidationError):
            self.env["work.center.area"].create(
                {
                    "name": "Third Area",
                    "code": "test_area_3",
                    "model_ids": [(6, 0, self.doc_model.ids)],
                }
            )

    def test_area_with_work_centers_cannot_be_deleted(self):
        with self.assertRaises(UserError):
            self.area.unlink()

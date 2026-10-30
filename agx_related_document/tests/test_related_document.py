from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


def _owner_only(self, operation):
    """Test records are readable by their owner only."""
    return self.filtered(lambda r: self.env.su or r.owner_id == self.env.user)


class TestCiting(models.TransientModel):
    _name = "test.related.document.citing"
    _description = "Test citing document"
    _inherit = ["mail.thread", "related.document.mixin"]

    name = fields.Char()
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    _filter_access_rules = _filter_access_rules_python = _owner_only


class TestTarget(models.TransientModel):
    _name = "test.related.document.target"
    _description = "Test cited document"

    name = fields.Char()
    number = fields.Char()
    state = fields.Char(default="approved")
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    _filter_access_rules = _filter_access_rules_python = _owner_only

    @api.model
    def _search(self, args, **kwargs):
        if not self.env.su:
            args = list(args) + [("owner_id", "=", self.env.uid)]
        return super()._search(args, **kwargs)


@tagged("post_install", "-at_install")
class TestRelatedDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for model in (TestCiting, TestTarget):
            model._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            [TestCiting._name, TestTarget._name],
            {"module": "agx_related_document"},
        )
        # Transient models carry no ACL of their own in this test registry.
        for model in (TestCiting, TestTarget):
            cls.env["ir.model.access"].create(
                {
                    "name": model._name,
                    "model_id": cls.env["ir.model"]._get_id(model._name),
                    "group_id": cls.env.ref("base.group_user").id,
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": True,
                    "perm_unlink": True,
                }
            )
        Users = cls.env["res.users"]
        group = cls.env.ref("base.group_user")
        cls.owner = Users.create(
            {"name": "RD owner", "login": "rd_owner", "groups_id": [(6, 0, group.ids)]}
        )
        cls.other = Users.create(
            {"name": "RD other", "login": "rd_other", "groups_id": [(6, 0, group.ids)]}
        )
        cls.citing = cls.env["test.related.document.citing"].create(
            {"name": "Citing", "owner_id": cls.owner.id}
        )
        # Not readable by the owner: the user cannot reach it by dropdown.
        cls.target = cls.env["test.related.document.target"].create(
            {"name": "เรื่องทดสอบ", "number": "T-0001", "owner_id": cls.other.id}
        )
        cls.own_target = cls.env["test.related.document.target"].create(
            {"name": "ของฉัน", "number": "T-0002", "owner_id": cls.owner.id}
        )
        Fields = cls.env["ir.model.fields"]
        cls.kind = cls.env["related.document.kind"].create(
            {
                "name": "Test kind",
                "model_id": cls.env["ir.model"]._get_id(TestTarget._name),
                "number_field_id": Fields._get(TestTarget._name, "number").id,
                "subject_field_id": Fields._get(TestTarget._name, "name").id,
            }
        )

    def _add(self, user=None, **vals):
        return (
            self.env["related.document"]
            .with_user(user or self.owner)
            .create(
                dict(
                    {
                        "res_model": self.citing._name,
                        "res_id": self.citing.id,
                        "document_number": "อว 0001/1",
                        "name": "หนังสือ",
                    },
                    **vals,
                )
            )
        )

    def _cite(self, user=None, **vals):
        return self._add(
            user,
            kind_id=self.kind.id,
            document_number=vals.pop("number", False),
            name=False,
            **vals,
        )

    # Dropdown under the user's rights, typed number under sudo on request.

    def test_picked_document_the_user_reads(self):
        row = self._cite(target_res_id=self.own_target.id)
        self.assertEqual(row.document_number, "T-0002")
        self.assertEqual(row.name, "ของฉัน")

    def test_picked_document_the_user_cannot_read_is_refused(self):
        with self.assertRaises(ValidationError):
            self._cite(target_res_id=self.target.id)

    def test_picked_unreadable_allowed_with_number_lookup(self):
        self.kind.allow_number_lookup = True
        row = self._cite(target_res_id=self.target.id)
        self.assertEqual(row.document_number, "T-0001")

    def test_forged_target_id_refused(self):
        with self.assertRaises(ValidationError):
            self._cite(target_res_id=self.target.id + 9999)

    def test_number_lookup_off_finds_only_readable(self):
        with self.assertRaises(ValidationError):
            self._cite(number="T-0001")
        row = self._cite(number=" t-0002 ")
        self.assertEqual(row.target_res_id, self.own_target.id)
        self.assertEqual(row.document_number, "T-0002")

    def test_number_lookup_on_crosses_rights(self):
        self.kind.allow_number_lookup = True
        row = self._cite(number="T-0001")
        self.assertEqual(row.target_res_id, self.target.id)
        self.assertEqual(row.name, "เรื่องทดสอบ")

    def test_target_domain_applies_to_pick_and_number(self):
        self.kind.write(
            {"allow_number_lookup": True, "target_domain": "[('state', '=', 'done')]"}
        )
        with self.assertRaises(ValidationError):
            self._cite(number="T-0001")
        with self.assertRaises(ValidationError):
            self._cite(target_res_id=self.own_target.id)
        self.own_target.state = "done"
        self.assertTrue(self._cite(target_res_id=self.own_target.id))

    def test_kind_scope_citing_models(self):
        self.kind.citing_model_ids = [
            (6, 0, [self.env["ir.model"]._get_id("res.partner")])
        ]
        with self.assertRaises(ValidationError):
            self._cite(target_res_id=self.own_target.id)
        self.kind.citing_model_ids = [
            (6, 0, [self.env["ir.model"]._get_id(self.citing._name)])
        ]
        self.assertTrue(self._cite(target_res_id=self.own_target.id))

    def test_row_needs_number_or_subject(self):
        with self.assertRaises(ValidationError):
            self._add(document_number=False, name=False)

    # Reading follows the citing document.

    def test_rows_invisible_when_citing_unreadable(self):
        row = self._add()
        Rows = self.env["related.document"]
        self.assertIn(row, Rows.with_user(self.owner).search([]))
        self.assertNotIn(row, Rows.with_user(self.other).search([]))
        row.invalidate_recordset()
        with self.assertRaises(AccessError):
            row.with_user(self.other).read(["name"])

    def test_cited_by_lists_only_readable_citing(self):
        self.kind.allow_number_lookup = True
        row = self._cite(number="T-0001")
        listed = self.env["related.document"]._action_cited_by(self.target)
        self.assertEqual(listed["domain"], [("id", "in", row.ids)])
        as_other = self.env["related.document"].with_user(self.other)
        self.assertEqual(
            as_other._action_cited_by(self.target)["domain"], [("id", "in", [])]
        )

    def test_cited_by_server_action_follows_the_kind(self):
        Action = self.env["ir.actions.server"]
        domain = [("code", "like", "_action_cited_by")]
        self.assertFalse(Action.search(domain))
        self.kind.show_cited_by = True
        self.assertEqual(Action.search(domain).binding_model_id.model, TestTarget._name)
        self.kind.show_cited_by = False
        self.assertFalse(Action.search(domain))

    # Opening the cited document.

    def test_open_as_reader_only(self):
        self.kind.allow_number_lookup = True
        row = self._cite(number="T-0001")
        with self.assertRaisesRegex(UserError, "ไม่มีสิทธิ์"):
            row.action_open_document()
        action = row.with_user(self.other).action_open_document()
        self.assertEqual(action["res_id"], self.target.id)

    def test_open_deleted_target(self):
        row = self._cite(target_res_id=self.own_target.id)
        self.own_target.unlink()
        with self.assertRaisesRegex(UserError, "ถูกลบแล้ว"):
            row.action_open_document()
        self.assertEqual(row.document_number, "T-0002")

    # Lifecycle and who may change rows.

    def test_change_logged_and_follows_hook(self):
        messages = len(self.citing.message_ids)
        row = self._add()
        self.assertGreater(len(self.citing.message_ids), messages)
        # `other` cannot write the citing record, so cannot change its rows.
        with self.assertRaises(AccessError):
            row.with_user(self.other).unlink()
        row.unlink()
        self.assertFalse(row.exists())

    def test_citing_deleted_deletes_rows(self):
        row = self._add()
        self.citing.unlink()
        self.assertFalse(row.exists())

    def test_not_copied(self):
        self._add()
        self.assertFalse(self.citing.copy().related_document_ids)

    def test_citing_model_without_mixin_refused(self):
        partner = self.env["res.partner"].create({"name": "No mixin"})
        with self.assertRaises(ValidationError):
            self.env["related.document"].with_user(self.owner).create(
                {"res_model": "res.partner", "res_id": partner.id, "name": "x"}
            )

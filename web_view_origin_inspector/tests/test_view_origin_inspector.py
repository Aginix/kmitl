from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestViewOriginInspector(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.View = cls.env["ir.ui.view"]
        cls.Log = cls.env["ir.ui.view.change.log"]
        cls.base = cls.View.create(
            {
                "name": "test.origin.base",
                "model": "res.partner",
                "type": "form",
                "arch": """
                    <form>
                        <header>
                            <button name="action_archive" type="object" string="X"/>
                        </header>
                        <field name="name"/>
                        <field name="child_ids">
                            <tree><field name="name"/></tree>
                        </field>
                    </form>""",
            }
        )
        cls.ext_attr = cls.View.create(
            {
                "name": "test.origin.attr",
                "model": "res.partner",
                "inherit_id": cls.base.id,
                "arch": """
                    <button name="action_archive" position="attributes">
                        <attribute name="string">Y</attribute>
                    </button>""",
            }
        )
        cls.ext_add = cls.View.create(
            {
                "name": "test.origin.add",
                "model": "res.partner",
                "inherit_id": cls.base.id,
                "arch": """
                    <button name="action_archive" position="after">
                        <button name="action_unarchive" type="object" string="Z"/>
                    </button>""",
            }
        )

    def _inspect(self, tag, name, parent_field=False, area=False):
        return self.View.view_origin_inspect(
            self.base.id, tag, name, parent_field=parent_field, area=area
        )

    def test_declared_then_attributes_changed(self):
        [occ] = self._inspect("button", "action_archive", area="header")[
            "occurrences"
        ]
        self.assertTrue(occ["matched"])
        self.assertEqual(
            [(e["view_id"], e["kind"]) for e in occ["events"]],
            [(self.base.id, "declared"), (self.ext_attr.id, "attributes")],
        )
        self.assertEqual(
            occ["events"][1]["changes"], [{"attr": "string", "old": "X", "new": "Y"}]
        )
        self.assertEqual(occ["xpath"], "//button[@name='action_archive']")

    def test_added_by_extension(self):
        [occ] = self._inspect("button", "action_unarchive")["occurrences"]
        self.assertEqual(
            [(e["view_id"], e["kind"]) for e in occ["events"]],
            [(self.ext_add.id, "added")],
        )

    def test_duplicate_field_matches_clicked_subview(self):
        occurrences = self._inspect("field", "name", "child_ids", "tree")[
            "occurrences"
        ]
        self.assertEqual([o["matched"] for o in occurrences], [True, False])
        self.assertEqual(
            occurrences[0]["xpath"], "//field[@name='child_ids']/tree/field[@name='name']"
        )

    def test_hide_creates_view_and_log(self):
        xpath = "//button[@name='action_archive']"
        view_id = self.View.view_origin_hide(
            self.base.id, "button", "action_archive", xpath
        )
        arch = self.base._get_combined_arch()
        self.assertEqual(arch.xpath(xpath)[0].get("invisible"), "1")
        log = self.Log.search([("view_id", "=", view_id)])
        self.assertEqual(log.operation, "hide")
        self.assertEqual(log.target_xpath, xpath)
        log.action_revert_hide()
        self.assertFalse(self.View.browse(view_id).exists())
        self.assertEqual(log.state, "reverted")

    def test_manual_write_logged(self):
        self.ext_attr.write({"name": "renamed"})
        self.assertFalse(
            self.Log.search([("view_id", "=", self.ext_attr.id), ("operation", "=", "write")])
        )
        self.ext_attr.write({"active": False})
        log = self.Log.search(
            [("view_id", "=", self.ext_attr.id), ("operation", "=", "write")]
        )
        self.assertIn("active=True", log.arch_before)
        self.assertIn("active=False", log.arch_after)
        self.assertTrue(log.arch_diff)

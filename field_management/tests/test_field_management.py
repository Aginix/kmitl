# -*- coding: utf-8 -*-
import json

from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFieldManagement(TransactionCase):
    """Comprehensive tests for the field_management module.

    Covers three test layers:
      A) _extract_domain_fields  – pure domain parsing
      B) _build_modifier_rules   – rule builder logic
      C) _apply_modifier_rules   – XML patching
      D-F) get_view per modifier type (readonly / invisible / required)
      G) All three modifiers simultaneously
      H) Invisible field injection
      I) Non-form views skipped
      J) Inactive config ignored
      K) Multi-config OR logic
      L) Computed fields on management.fields models
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env["ir.model"]
        IrField = cls.env["ir.model.fields"]

        cls.partner_model = IrModel.search([("model", "=", "res.partner")], limit=1)

        def _f(name):
            return IrField.search(
                [("model", "=", "res.partner"), ("name", "=", name)], limit=1
            )

        cls.field_name = _f("name")
        cls.field_email = _f("email")
        cls.field_phone = _f("phone")
        cls.field_street = _f("street")
        cls.field_active = _f("active")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_readonly_config(self, apply_on_domain=False, field_specs=None):
        field_lines = [
            (
                0,
                0,
                {
                    "field_id": spec["field_id"].id,
                    "domain": spec.get("domain") or False,
                    "force_readonly": spec.get("force_readonly", True),
                },
            )
            for spec in (field_specs or [])
        ]
        return self.env["readonly.management"].create(
            {
                "name": "Test Readonly Config",
                "model_id": self.partner_model.id,
                "apply_on_domain": apply_on_domain or False,
                "field_ids": field_lines,
            }
        )

    def _make_invisible_config(self, apply_on_domain=False, field_specs=None):
        field_lines = [
            (
                0,
                0,
                {
                    "field_id": spec["field_id"].id,
                    "domain": spec.get("domain") or False,
                    "force_invisible": spec.get("force_invisible", True),
                },
            )
            for spec in (field_specs or [])
        ]
        return self.env["invisible.management"].create(
            {
                "name": "Test Invisible Config",
                "model_id": self.partner_model.id,
                "apply_on_domain": apply_on_domain or False,
                "field_ids": field_lines,
            }
        )

    def _make_required_config(self, apply_on_domain=False, field_specs=None):
        field_lines = [
            (
                0,
                0,
                {
                    "field_id": spec["field_id"].id,
                    "domain": spec.get("domain") or False,
                    "force_required": spec.get("force_required", True),
                },
            )
            for spec in (field_specs or [])
        ]
        return self.env["required.management"].create(
            {
                "name": "Test Required Config",
                "model_id": self.partner_model.id,
                "apply_on_domain": apply_on_domain or False,
                "field_ids": field_lines,
            }
        )

    def _get_partner_form_arch(self):
        """Return (result, lxml doc) for the res.partner form view."""
        result = self.env["res.partner"].get_view(view_type="form")
        doc = etree.fromstring(result["arch"].encode())
        return result, doc

    def _get_modifiers(self, doc, field_name):
        """Return the modifiers dict for the first matching field node, or {}."""
        nodes = doc.xpath(f"//field[@name='{field_name}']")
        if not nodes:
            return {}
        return json.loads(nodes[0].get("modifiers", "{}"))

    def _field_node_exists(self, doc, field_name):
        return bool(doc.xpath(f"//field[@name='{field_name}']"))

    def _clean_partner_configs(self):
        """Remove all management configs for res.partner."""
        domain = [("model_id.model", "=", "res.partner")]
        self.env["readonly.management"].sudo().search(domain).unlink()
        self.env["invisible.management"].sudo().search(domain).unlink()
        self.env["required.management"].sudo().search(domain).unlink()

    # ------------------------------------------------------------------
    # Group A: _extract_domain_fields
    # ------------------------------------------------------------------

    def test_a1_extract_simple_leaf(self):
        """Simple single-leaf domain → returns the one field name."""
        partner = self.env["res.partner"]
        result = partner._extract_domain_fields([("active", "=", True)])
        self.assertEqual(result, {"active"})

    def test_a2_extract_multiple_leaves(self):
        """Multi-leaf domain → all field names extracted."""
        partner = self.env["res.partner"]
        domain = [("active", "=", True), ("name", "!=", False)]
        result = partner._extract_domain_fields(domain)
        self.assertEqual(result, {"active", "name"})

    def test_a3_extract_nested_or_domain(self):
        """Nested OR domain → field names from all leaves."""
        partner = self.env["res.partner"]
        domain = ["|", ("active", "=", True), ("email", "!=", False)]
        result = partner._extract_domain_fields(domain)
        self.assertEqual(result, {"active", "email"})

    def test_a4_extract_empty_domain(self):
        """Empty domain → empty set."""
        partner = self.env["res.partner"]
        result = partner._extract_domain_fields([])
        self.assertEqual(result, set())

    # ------------------------------------------------------------------
    # Group B: _build_modifier_rules
    # ------------------------------------------------------------------

    def test_b1_build_rules_force_no_apply_domain(self):
        """force_readonly=True with no apply_on_domain → rule is literal True."""
        cfg = self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        self.assertIn("name", rules)
        self.assertIs(rules["name"][0], True)
        self.assertEqual(req, set())

    def test_b2_build_rules_force_with_apply_domain(self):
        """force_readonly=True + apply_on_domain → rule is the apply domain."""
        cfg = self._make_readonly_config(
            apply_on_domain="[('active', '=', True)]",
            field_specs=[{"field_id": self.field_name, "force_readonly": True}],
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        self.assertEqual(rules["name"][0], [("active", "=", True)])
        # apply_on_domain references 'active' → must appear in req fields
        self.assertIn("active", req)

    def test_b3_build_rules_no_force_no_domain(self):
        """No force, no domain → rule is literal True."""
        cfg = self._make_readonly_config(
            field_specs=[
                {"field_id": self.field_email, "force_readonly": False, "domain": False}
            ]
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        self.assertIs(rules["email"][0], True)
        self.assertEqual(req, set())

    def test_b4_build_rules_field_domain_only(self):
        """No force, field domain only → rule equals the field domain."""
        cfg = self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        self.assertEqual(rules["email"][0], [("active", "=", True)])
        self.assertIn("active", req)

    def test_b5_build_rules_apply_domain_and_field_domain_combined(self):
        """apply_on_domain + field domain → combined with AND."""
        cfg = self._make_readonly_config(
            apply_on_domain="[('active', '=', True)]",
            field_specs=[
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('name', '!=', False)]",
                }
            ],
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        combined = rules["email"][0]
        self.assertIsInstance(combined, list)
        combined_str = str(combined)
        self.assertIn("active", combined_str)
        self.assertIn("name", combined_str)
        self.assertIn("active", req)
        self.assertIn("name", req)

    def test_b6_build_rules_invalid_apply_domain_skips_config(self):
        """Invalid apply_on_domain → entire config is skipped."""
        cfg = self._make_readonly_config(
            apply_on_domain="not valid python {{",
            field_specs=[{"field_id": self.field_name, "force_readonly": True}],
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        self.assertNotIn("name", rules)
        self.assertEqual(req, set())

    def test_b7_build_rules_invalid_field_domain_skips_field_only(self):
        """Invalid field domain → that field skipped; sibling fields still processed."""
        cfg = self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_name,
                    "force_readonly": False,
                    "domain": "not valid {{",
                },
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                },
            ]
        )
        partner = self.env["res.partner"]
        rules, req = partner._build_modifier_rules(
            [cfg], "readonly.management", "force_readonly"
        )
        self.assertNotIn("name", rules)
        self.assertIn("email", rules)

    def test_b8_build_rules_multiple_configs_same_field(self):
        """Two configs targeting the same field → two entries in the rule list."""
        cfg1 = self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_name,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        cfg2 = self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_name,
                    "force_readonly": False,
                    "domain": "[('email', '!=', False)]",
                }
            ]
        )
        partner = self.env["res.partner"]
        rules, _ = partner._build_modifier_rules(
            [cfg1, cfg2], "readonly.management", "force_readonly"
        )
        self.assertEqual(len(rules["name"]), 2)

    # ------------------------------------------------------------------
    # Group C: _apply_modifier_rules
    # ------------------------------------------------------------------

    def test_c1_apply_true_domain(self):
        """[True] → modifier is JSON true."""
        arch = "<form><field name='name'/></form>"
        doc = etree.fromstring(arch)
        self.env["res.partner"]._apply_modifier_rules(doc, {"name": [True]}, "readonly")
        modifiers = json.loads(doc.xpath("//field[@name='name']")[0].get("modifiers", "{}"))
        self.assertIs(modifiers.get("readonly"), True)

    def test_c2_apply_single_domain_list(self):
        """Single domain list → modifier equals that domain (JSON serialises tuples as lists)."""
        domain = [["active", "=", True]]
        arch = "<form><field name='email'/></form>"
        doc = etree.fromstring(arch)
        self.env["res.partner"]._apply_modifier_rules(
            doc, {"email": [domain]}, "invisible"
        )
        modifiers = json.loads(doc.xpath("//field[@name='email']")[0].get("modifiers", "{}"))
        self.assertEqual(modifiers.get("invisible"), domain)

    def test_c3_apply_multiple_domains_or_combined(self):
        """Multiple non-True domains → OR combined."""
        d1 = [("active", "=", True)]
        d2 = [("email", "!=", False)]
        arch = "<form><field name='name'/></form>"
        doc = etree.fromstring(arch)
        self.env["res.partner"]._apply_modifier_rules(
            doc, {"name": [d1, d2]}, "required"
        )
        modifiers = json.loads(doc.xpath("//field[@name='name']")[0].get("modifiers", "{}"))
        result_str = str(modifiers.get("required", ""))
        self.assertIn("active", result_str)
        self.assertIn("email", result_str)

    def test_c4_apply_true_wins_over_domain(self):
        """If any domain is True, the modifier collapses to True."""
        arch = "<form><field name='name'/></form>"
        doc = etree.fromstring(arch)
        self.env["res.partner"]._apply_modifier_rules(
            doc, {"name": [[("active", "=", True)], True]}, "readonly"
        )
        modifiers = json.loads(doc.xpath("//field[@name='name']")[0].get("modifiers", "{}"))
        self.assertIs(modifiers.get("readonly"), True)

    def test_c5_apply_field_absent_from_arch_no_crash(self):
        """Field absent from arch → no crash, existing nodes untouched."""
        arch = "<form><field name='email'/></form>"
        doc = etree.fromstring(arch)
        # 'name' is not in the arch — should be a safe no-op
        self.env["res.partner"]._apply_modifier_rules(
            doc, {"name": [True]}, "readonly"
        )
        email_modifiers = json.loads(
            doc.xpath("//field[@name='email']")[0].get("modifiers", "{}")
        )
        self.assertNotIn("readonly", email_modifiers)

    def test_c6_apply_preserves_existing_modifiers(self):
        """New modifier key is merged into existing modifiers, not overwritten."""
        arch = "<form><field name='name' modifiers='{\"invisible\": true}'/></form>"
        doc = etree.fromstring(arch)
        self.env["res.partner"]._apply_modifier_rules(
            doc, {"name": [True]}, "readonly"
        )
        modifiers = json.loads(doc.xpath("//field[@name='name']")[0].get("modifiers", "{}"))
        self.assertIs(modifiers.get("readonly"), True)
        self.assertIs(modifiers.get("invisible"), True)

    # ------------------------------------------------------------------
    # Group D: get_view – readonly modifier
    # ------------------------------------------------------------------

    def test_d1_get_view_no_configs_returns_unchanged(self):
        """No configs → fast-path return, no readonly modifier injected on 'name'."""
        self._clean_partner_configs()
        _, doc = self._get_partner_form_arch()
        modifiers = self._get_modifiers(doc, "name")
        self.assertNotIn("readonly", modifiers)

    def test_d2_get_view_force_readonly(self):
        """force_readonly=True → modifier['readonly'] = True on the target field."""
        self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        _, doc = self._get_partner_form_arch()
        self.assertIs(self._get_modifiers(doc, "name").get("readonly"), True)

    def test_d3_get_view_readonly_with_conditional_domain(self):
        """Conditional domain → modifier is the parsed domain (tuples become lists via JSON)."""
        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        modifier = self._get_modifiers(doc, "email").get("readonly")
        self.assertEqual(modifier, [["active", "=", True]])

    def test_d4_get_view_apply_on_domain_scopes_force_field(self):
        """apply_on_domain + force_readonly → modifier value is the apply domain."""
        self._make_readonly_config(
            apply_on_domain="[('active', '=', True)]",
            field_specs=[{"field_id": self.field_phone, "force_readonly": True}],
        )
        _, doc = self._get_partner_form_arch()
        modifier = self._get_modifiers(doc, "phone").get("readonly")
        self.assertEqual(modifier, [["active", "=", True]])

    # ------------------------------------------------------------------
    # Group E: get_view – invisible modifier
    # ------------------------------------------------------------------

    def test_e1_get_view_force_invisible(self):
        """force_invisible=True → modifier['invisible'] = True."""
        self._make_invisible_config(
            field_specs=[{"field_id": self.field_street, "force_invisible": True}]
        )
        _, doc = self._get_partner_form_arch()
        self.assertIs(self._get_modifiers(doc, "street").get("invisible"), True)

    def test_e2_get_view_invisible_with_conditional_domain(self):
        """Conditional invisible domain → modifier is the parsed domain."""
        self._make_invisible_config(
            field_specs=[
                {
                    "field_id": self.field_phone,
                    "force_invisible": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        modifier = self._get_modifiers(doc, "phone").get("invisible")
        self.assertEqual(modifier, [["active", "=", True]])

    # ------------------------------------------------------------------
    # Group F: get_view – required modifier
    # ------------------------------------------------------------------

    def test_f1_get_view_force_required(self):
        """force_required=True → modifier['required'] = True."""
        self._make_required_config(
            field_specs=[{"field_id": self.field_email, "force_required": True}]
        )
        _, doc = self._get_partner_form_arch()
        self.assertIs(self._get_modifiers(doc, "email").get("required"), True)

    def test_f2_get_view_required_with_conditional_domain(self):
        """Conditional required domain → modifier is the parsed domain."""
        self._make_required_config(
            field_specs=[
                {
                    "field_id": self.field_phone,
                    "force_required": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        modifier = self._get_modifiers(doc, "phone").get("required")
        self.assertEqual(modifier, [["active", "=", True]])

    # ------------------------------------------------------------------
    # Group G: All three modifier types simultaneously
    # ------------------------------------------------------------------

    def test_g1_all_three_modifiers_on_separate_fields(self):
        """Three configs, three different fields → each gets its own modifier."""
        self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        self._make_invisible_config(
            field_specs=[{"field_id": self.field_email, "force_invisible": True}]
        )
        self._make_required_config(
            field_specs=[{"field_id": self.field_phone, "force_required": True}]
        )
        _, doc = self._get_partner_form_arch()
        self.assertIs(self._get_modifiers(doc, "name").get("readonly"), True)
        self.assertIs(self._get_modifiers(doc, "email").get("invisible"), True)
        self.assertIs(self._get_modifiers(doc, "phone").get("required"), True)

    def test_g2_same_field_gets_multiple_modifier_types(self):
        """Readonly + required on the same field → both modifiers are set."""
        self._make_readonly_config(
            field_specs=[{"field_id": self.field_email, "force_readonly": True}]
        )
        self._make_required_config(
            field_specs=[{"field_id": self.field_email, "force_required": True}]
        )
        _, doc = self._get_partner_form_arch()
        modifiers = self._get_modifiers(doc, "email")
        self.assertIs(modifiers.get("readonly"), True)
        self.assertIs(modifiers.get("required"), True)

    # ------------------------------------------------------------------
    # Group H: Invisible field injection
    # ------------------------------------------------------------------

    def test_h1_domain_referenced_field_present_in_arch(self):
        """A field used in a domain condition must appear in the rendered arch."""
        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        # 'active' must be in the arch (pre-existing or injected)
        self.assertTrue(self._field_node_exists(doc, "active"))

    def test_h2_injected_field_has_invisible_attribute(self):
        """A field injected for domain evaluation must carry invisible='1'."""
        # Find a field that is not present in the default partner form arch
        result_pre = self.env["res.partner"].get_view(view_type="form")
        doc_pre = etree.fromstring(result_pre["arch"].encode())

        barcode_field = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "barcode")], limit=1
        )
        if not barcode_field:
            self.skipTest("barcode field does not exist on res.partner")
        if self._field_node_exists(doc_pre, "barcode"):
            self.skipTest("barcode already present in partner form arch")

        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('barcode', '!=', False)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        injected = doc.xpath("//field[@name='barcode']")
        self.assertTrue(injected, "barcode node was not injected into the arch")
        self.assertEqual(injected[0].get("invisible"), "1")

    def test_h3_required_fields_union_across_all_modifier_types(self):
        """Fields from all three modifier-type domains are all present in the arch."""
        # Use three distinct condition fields via the domain of each modifier type
        # We ensure 'active' is used as condition field for all three
        # (it may already be there, but the logic path is exercised regardless)
        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_email,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        self._make_invisible_config(
            field_specs=[
                {
                    "field_id": self.field_phone,
                    "force_invisible": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        self._make_required_config(
            field_specs=[
                {
                    "field_id": self.field_street,
                    "force_required": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        self.assertTrue(self._field_node_exists(doc, "active"))

    # ------------------------------------------------------------------
    # Group I: Non-form views are not modified
    # ------------------------------------------------------------------

    def test_i1_tree_view_not_modified(self):
        """Tree (list) view is returned without any field_management modifiers."""
        self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        result = self.env["res.partner"].get_view(view_type="tree")
        doc = etree.fromstring(result["arch"].encode())
        # The 'name' field in a tree view should have no readonly injected by us
        modifiers = self._get_modifiers(doc, "name")
        self.assertNotIn("readonly", modifiers)

    # ------------------------------------------------------------------
    # Group J: Inactive config is ignored
    # ------------------------------------------------------------------

    def test_j1_inactive_config_has_no_effect(self):
        """Config with active=False must not inject any modifier."""
        cfg = self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        cfg.active = False
        _, doc = self._get_partner_form_arch()
        modifiers = self._get_modifiers(doc, "name")
        self.assertNotIn("readonly", modifiers)

    # ------------------------------------------------------------------
    # Group K: Multiple configs for the same field (OR logic)
    # ------------------------------------------------------------------

    def test_k1_two_conditional_configs_or_combined(self):
        """Two conditional configs on the same field → OR of both domains."""
        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_name,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_name,
                    "force_readonly": False,
                    "domain": "[('email', '!=', False)]",
                }
            ]
        )
        _, doc = self._get_partner_form_arch()
        modifier = self._get_modifiers(doc, "name").get("readonly")
        self.assertIsNotNone(modifier)
        modifier_str = str(modifier)
        self.assertIn("active", modifier_str)
        self.assertIn("email", modifier_str)

    def test_k2_force_config_wins_over_conditional(self):
        """One force + one conditional on the same field → True wins."""
        self._make_readonly_config(
            field_specs=[
                {
                    "field_id": self.field_name,
                    "force_readonly": False,
                    "domain": "[('active', '=', True)]",
                }
            ]
        )
        self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        _, doc = self._get_partner_form_arch()
        self.assertIs(self._get_modifiers(doc, "name").get("readonly"), True)

    # ------------------------------------------------------------------
    # Group L: Computed fields on management.fields models
    # ------------------------------------------------------------------

    def test_l1_used_field_ids_reflects_all_sibling_fields(self):
        """used_field_ids contains all fields configured in the same management record."""
        cfg = self._make_readonly_config(
            field_specs=[
                {"field_id": self.field_name, "force_readonly": True},
                {"field_id": self.field_email, "force_readonly": True},
            ]
        )
        first_line = cfg.field_ids[0]
        self.assertIn(self.field_name, first_line.used_field_ids)
        self.assertIn(self.field_email, first_line.used_field_ids)

    def test_l2_used_model_reflects_config_model(self):
        """used_model is the same model as the parent management config."""
        cfg = self._make_readonly_config(
            field_specs=[{"field_id": self.field_name, "force_readonly": True}]
        )
        self.assertEqual(cfg.field_ids[0].used_model, self.partner_model)

    def test_l3_used_field_ids_and_used_model_false_without_management_id(self):
        """Without a management_id, used_field_ids and used_model are empty."""
        line = self.env["readonly.management.fields"].new(
            {"field_id": self.field_name.id}
        )
        self.assertFalse(line.used_field_ids)
        self.assertFalse(line.used_model)

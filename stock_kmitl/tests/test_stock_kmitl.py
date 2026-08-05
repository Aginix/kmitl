# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.stock_kmitl.hooks import post_init_hook


@tagged("post_install", "-at_install")
class TestStockInventoryKmitl(TransactionCase):
    """stock.inventory additions merged from stock_inventory_kmitl /
    stock_inventory_department."""

    def test_name_default(self):
        # _default_inventory_name -> "Inventory Adjustment DD-MM-YYYY"
        name = self.env["stock.inventory"].default_get(["name"])["name"]
        self.assertTrue(
            name.startswith("Inventory Adjustment "),
            "name default should be prefixed with 'Inventory Adjustment '",
        )
        expected = "Inventory Adjustment " + datetime.today().strftime("%d-%m-%Y")
        self.assertEqual(name, expected)

    def test_responsible_id_default_is_current_user(self):
        defaults = self.env["stock.inventory"].default_get(["responsible_id"])
        # default_get may serialize a Many2one default as an id or a recordset
        self.assertIn(
            defaults.get("responsible_id"), (self.env.uid, self.env.user)
        )

    def test_department_field(self):
        field = self.env["stock.inventory"]._fields["department_id"]
        self.assertEqual(field.type, "many2one")
        self.assertEqual(field.comodel_name, "hr.department")
        dept = self.env["hr.department"].create({"name": "Test Dept"})
        inventory = self.env["stock.inventory"].new({"department_id": dept.id})
        self.assertEqual(inventory.department_id, dept)


@tagged("post_install", "-at_install")
class TestStockScrapKmitl(TransactionCase):
    """stock.scrap additions merged from stock_scrap_responsible_user,
    stock_scrap_reason_text, stock_scrap_origin_readonly_done and
    stock_scrap_attachment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Test Scrap Product", "type": "consu"}
        )

    def _new_scrap(self, **vals):
        values = {
            "product_id": self.product.id,
            "product_uom_id": self.product.uom_id.id,
            "scrap_qty": 1.0,
        }
        values.update(vals)
        return self.env["stock.scrap"].create(values)

    def test_user_id_default_is_current_user(self):
        scrap = self._new_scrap()
        self.assertEqual(scrap.user_id, self.env.user)

    def test_reason_field(self):
        field = self.env["stock.scrap"]._fields["reason"]
        self.assertEqual(field.type, "text")
        scrap = self._new_scrap(reason="Damaged on arrival")
        self.assertEqual(scrap.reason, "Damaged on arrival")

    def test_origin_field_settable(self):
        # origin is a core field; the merge only made it readonly-when-done
        # (a view modifier). Confirm it remains a usable Char.
        scrap = self._new_scrap(origin="PO00042")
        self.assertEqual(scrap.origin, "PO00042")

    def test_attachment_ids_is_scoped_many2many(self):
        field = self.env["stock.scrap"]._fields["attachment_ids"]
        self.assertEqual(field.type, "many2many")
        self.assertEqual(field.comodel_name, "ir.attachment")
        # the merge fix: scope the relation to this model's attachments and
        # tag newly created ones with the right res_model
        self.assertEqual(field.domain, [("res_model", "=", "stock.scrap")])
        self.assertEqual(field.context, {"default_res_model": "stock.scrap"})

    def test_attachment_ids_link(self):
        scrap = self._new_scrap()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "evidence.pdf",
                "res_model": "stock.scrap",
                "res_id": scrap.id,
            }
        )
        scrap.write({"attachment_ids": [(4, attachment.id)]})
        self.assertIn(attachment, scrap.attachment_ids)


@tagged("post_install", "-at_install")
class TestStockKmitlSecurity(TransactionCase):
    """Inventory adjustment menu restriction merged from
    stock_inventory_restriction."""

    def test_group_exists(self):
        group = self.env.ref("stock_kmitl.can_do_inventory_adjustment")
        self.assertTrue(group)

    def test_menu_restricted_to_group(self):
        group = self.env.ref("stock_kmitl.can_do_inventory_adjustment")
        menu = self.env.ref("stock_inventory.menu_action_inventory_tree")
        self.assertIn(group, menu.groups_id)


@tagged("post_install", "-at_install")
class TestStockWarehouseHook(TransactionCase):
    """post_init_hook merged from stock_warehouse_kmitl."""

    def test_first_warehouse_set_to_kmitl(self):
        post_init_hook(self.env.cr, self.env.registry)
        self.env.invalidate_all()
        warehouse = self.env["stock.warehouse"].search(
            [], limit=1, order="id asc"
        )
        self.assertTrue(warehouse)
        self.assertEqual(warehouse.name, "KMITL")
        self.assertEqual(warehouse.code, "KMITL")
        self.assertFalse(warehouse.operating_unit_id)

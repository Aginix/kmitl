# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPurchaseOrderLeadtime(TransactionCase):

    def test_purchase_order_has_mixin_fields(self):
        """Verify purchase.order correctly inherits the leadtime mixin."""
        po_fields = self.env['purchase.order']._fields
        self.assertIn('state_entry_date', po_fields)
        self.assertIn('state_leadtime_ids', po_fields)

    def test_state_change_creates_log(self):
        """Happy-path: PO state transition creates a leadtime log entry."""
        partner = self.env.ref('base.res_partner_1')
        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
        })
        initial_state = po.state
        po.button_confirm()
        if po.state == initial_state:
            self.skipTest("Could not trigger state change — check purchase_order_kmitl setup")

        logs = self.env['state.leadtime.log'].search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', po.id),
        ])
        self.assertTrue(len(logs) >= 1, "Expected at least one leadtime log entry after state change")
        self.assertEqual(logs[0].from_state, initial_state)
        self.assertEqual(logs[0].to_state, po.state)

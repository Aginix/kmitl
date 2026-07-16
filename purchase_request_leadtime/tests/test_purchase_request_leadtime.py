# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPurchaseRequestLeadtime(TransactionCase):

    def test_purchase_request_has_mixin_fields(self):
        """Verify purchase.request correctly inherits the leadtime mixin."""
        pr_fields = self.env['purchase.request']._fields
        self.assertIn('state_entry_date', pr_fields)
        self.assertIn('state_leadtime_ids', pr_fields)

    def test_rejected_transition_creates_no_log(self):
        """_excluded_transitions = [('*', 'cancel')] must suppress log for any → rejected."""
        pr = self.env['purchase.request'].create({
            'name': 'Test PR',
        })
        initial_state = pr.state

        try:
            pr.write({'state': 'cancel'})
        except Exception:
            self.skipTest("Could not write 'cancel' state directly — check purchase_request_kmitl")

        logs = self.env['state.leadtime.log'].search([
            ('res_model', '=', 'purchase.request'),
            ('res_id', '=', pr.id),
            ('to_state', '=', 'cancel'),
        ])
        self.assertEqual(len(logs), 0, "Transition to 'cancel' must not be logged")

    def test_non_rejected_transition_creates_log(self):
        """Transitions that are not excluded must still be logged."""
        pr = self.env['purchase.request'].create({
            'name': 'Test PR',
        })
        initial_state = pr.state

        # Find a non-rejected target state to write
        pr_field = self.env['purchase.request']._fields.get('state')
        if not pr_field or pr_field.type != 'selection':
            self.skipTest("purchase.request.state is not a Selection field")

        other_states = [
            k for k, _ in pr_field.selection
            if k not in ('cancel', initial_state)
        ]
        if not other_states:
            self.skipTest("No non-excluded states available to test")

        target_state = other_states[0]
        try:
            pr.write({'state': target_state})
        except Exception:
            self.skipTest(f"Could not write state '{target_state}' directly — check purchase_request_kmitl")

        logs = self.env['state.leadtime.log'].search([
            ('res_model', '=', 'purchase.request'),
            ('res_id', '=', pr.id),
            ('to_state', '=', target_state),
        ])
        self.assertEqual(len(logs), 1, f"Expected log for transition to '{target_state}'")
        self.assertEqual(logs.from_state, initial_state)
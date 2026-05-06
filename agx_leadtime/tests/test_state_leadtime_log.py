# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestStateLeadtimeLogImmutability(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.log = cls.env['state.leadtime.log'].create({
            'res_model': 'res.partner',
            'res_id': cls.env.ref('base.main_partner').id,
            'from_state': 'draft',
            'to_state': 'approved',
            'duration_minutes': 10.0,
        })

    def test_write_raises_user_error(self):
        with self.assertRaises(UserError):
            self.log.write({'duration_minutes': 999.0})

    def test_unlink_raises_user_error(self):
        with self.assertRaises(UserError):
            self.log.unlink()

    # --- get_stats ---

    def test_get_stats_single_entry(self):
        stats = self.env['state.leadtime.log'].get_stats(
            res_model='res.partner',
            from_state='draft',
            to_state='approved',
        )
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_minutes'], 10.0)
        self.assertAlmostEqual(stats['min_minutes'], 10.0)
        self.assertAlmostEqual(stats['max_minutes'], 10.0)

    def test_get_stats_no_match_returns_zeros(self):
        stats = self.env['state.leadtime.log'].get_stats(
            res_model='res.partner',
            from_state='nonexistent',
            to_state='nonexistent',
        )
        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['avg_minutes'], 0.0)
        self.assertEqual(stats['min_minutes'], 0.0)
        self.assertEqual(stats['max_minutes'], 0.0)

    # --- get_all_stats ---

    def test_get_all_stats_returns_list(self):
        result = self.env['state.leadtime.log'].get_all_stats('res.partner')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)
        entry = next((r for r in result if r['from_state'] == 'draft' and r['to_state'] == 'approved'), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['count'], 1)
        self.assertAlmostEqual(entry['avg_minutes'], 10.0)

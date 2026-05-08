# -*- coding: utf-8 -*-
from odoo import fields
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


@tagged('post_install', '-at_install')
class TestStateLeadtimeLogGetStats(TransactionCase):
    """Tests for get_stats: multi-entry statistics, res_ids, and latest_only."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env['state.leadtime.log']
        cls.partner_a = cls.env['res.partner'].create({'name': 'Leadtime Test A'})
        cls.partner_b = cls.env['res.partner'].create({'name': 'Leadtime Test B'})

    def _log(self, partner, duration, transition_date=None):
        vals = {
            'res_model': 'res.partner',
            'res_id': partner.id,
            'from_state': 'draft',
            'to_state': 'approved',
            'duration_minutes': duration,
        }
        if transition_date:
            vals['transition_date'] = transition_date
        return self.Log.create(vals)

    # --- multi-entry statistics ---

    def test_multiple_entries_avg_min_max_total(self):
        self._log(self.partner_a, 10.0)
        self._log(self.partner_b, 30.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved')
        self.assertEqual(stats['count'], 2)
        self.assertAlmostEqual(stats['avg_minutes'], 20.0)
        self.assertAlmostEqual(stats['min_minutes'], 10.0)
        self.assertAlmostEqual(stats['max_minutes'], 30.0)
        self.assertAlmostEqual(stats['total_minutes'], 40.0)

    def test_duration_zero_excluded_from_stats(self):
        """Entries with duration_minutes=0 are excluded by the domain filter."""
        self._log(self.partner_a, 0.0)
        self._log(self.partner_b, 20.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved')
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_minutes'], 20.0)

    # --- date filters ---

    def test_date_from_excludes_older_logs(self):
        self._log(self.partner_a, 10.0, '2025-01-01 00:00:00')
        self._log(self.partner_b, 40.0, '2026-06-01 00:00:00')
        cutoff = fields.Datetime.from_string('2026-01-01 00:00:00')
        stats = self.Log.get_stats('res.partner', 'draft', 'approved', date_from=cutoff)
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_minutes'], 40.0)

    def test_date_to_excludes_newer_logs(self):
        self._log(self.partner_a, 10.0, '2025-01-01 00:00:00')
        self._log(self.partner_b, 40.0, '2026-06-01 00:00:00')
        cutoff = fields.Datetime.from_string('2026-01-01 00:00:00')
        stats = self.Log.get_stats('res.partner', 'draft', 'approved', date_to=cutoff)
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_minutes'], 10.0)

    # --- res_ids ---

    def test_res_ids_filters_to_specified_records(self):
        self._log(self.partner_a, 10.0)
        self._log(self.partner_b, 50.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved',
                                   res_ids=[self.partner_a.id])
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_minutes'], 10.0)

    def test_res_ids_empty_list_returns_zeros(self):
        self._log(self.partner_a, 10.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved', res_ids=[])
        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['avg_minutes'], 0.0)

    def test_res_ids_none_includes_all_records(self):
        self._log(self.partner_a, 10.0)
        self._log(self.partner_b, 30.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved', res_ids=None)
        self.assertEqual(stats['count'], 2)
        self.assertAlmostEqual(stats['avg_minutes'], 20.0)

    def test_res_ids_excludes_nonmatching_records(self):
        self._log(self.partner_b, 50.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved',
                                   res_ids=[self.partner_a.id])
        self.assertEqual(stats['count'], 0)

    # --- latest_only ---

    def test_latest_only_no_effect_when_one_log_per_record(self):
        self._log(self.partner_a, 10.0)
        self._log(self.partner_b, 20.0)
        stats = self.Log.get_stats('res.partner', 'draft', 'approved', latest_only=True)
        self.assertEqual(stats['count'], 2)
        self.assertAlmostEqual(stats['avg_minutes'], 15.0)

    def test_latest_only_picks_newest_when_same_record_transitions_twice(self):
        """Simulates a PR that was reset and went through the same transition again."""
        self._log(self.partner_a, 10.0, '2026-01-01 00:00:00')   # older cycle
        self._log(self.partner_a, 60.0, '2026-06-01 00:00:00')   # newer cycle

        stats_all = self.Log.get_stats('res.partner', 'draft', 'approved',
                                       res_ids=[self.partner_a.id])
        self.assertEqual(stats_all['count'], 2)
        self.assertAlmostEqual(stats_all['avg_minutes'], 35.0)  # (10+60)/2

        stats_latest = self.Log.get_stats('res.partner', 'draft', 'approved',
                                          res_ids=[self.partner_a.id], latest_only=True)
        self.assertEqual(stats_latest['count'], 1)
        self.assertAlmostEqual(stats_latest['avg_minutes'], 60.0)

    def test_latest_only_keeps_one_per_res_id_across_multiple_records(self):
        """latest_only=True: count equals number of unique res_ids."""
        # partner_a: two cycles → keep newer (40.0)
        self._log(self.partner_a, 10.0, '2026-01-01 00:00:00')
        self._log(self.partner_a, 40.0, '2026-06-01 00:00:00')
        # partner_b: one cycle → keep (20.0)
        self._log(self.partner_b, 20.0, '2026-03-01 00:00:00')

        stats = self.Log.get_stats('res.partner', 'draft', 'approved', latest_only=True)
        self.assertEqual(stats['count'], 2)
        self.assertAlmostEqual(stats['avg_minutes'], 30.0)   # (40+20)/2
        self.assertAlmostEqual(stats['min_minutes'], 20.0)
        self.assertAlmostEqual(stats['max_minutes'], 40.0)

    def test_latest_only_false_uses_all_entries(self):
        self._log(self.partner_a, 10.0, '2026-01-01 00:00:00')
        self._log(self.partner_a, 40.0, '2026-06-01 00:00:00')
        self._log(self.partner_b, 20.0)

        stats = self.Log.get_stats('res.partner', 'draft', 'approved', latest_only=False)
        self.assertEqual(stats['count'], 3)
        self.assertAlmostEqual(stats['avg_minutes'], (10.0 + 40.0 + 20.0) / 3)

    def test_latest_only_combined_with_res_ids(self):
        """latest_only and res_ids can be used together."""
        self._log(self.partner_a, 10.0, '2026-01-01 00:00:00')
        self._log(self.partner_a, 50.0, '2026-06-01 00:00:00')  # newest for A → keep
        self._log(self.partner_b, 30.0)  # excluded by res_ids

        stats = self.Log.get_stats('res.partner', 'draft', 'approved',
                                   res_ids=[self.partner_a.id], latest_only=True)
        self.assertEqual(stats['count'], 1)
        self.assertAlmostEqual(stats['avg_minutes'], 50.0)
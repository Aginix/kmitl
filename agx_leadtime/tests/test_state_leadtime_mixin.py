# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class TestLeadtimeModel(models.TransientModel):
    _name = 'test.leadtime.model'
    _description = 'Test Model for Leadtime Mixin'
    _inherit = 'state.leadtime.mixin'

    name = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], default='draft')


class TestLeadtimeExclusionModel(models.TransientModel):
    _name = 'test.leadtime.exclusion'
    _description = 'Test Model with Excluded Transitions'
    _inherit = 'state.leadtime.mixin'

    name = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], default='draft')

    _excluded_transitions = [('*', 'rejected')]


class TestLeadtimeWhitelistModel(models.TransientModel):
    _name = 'test.leadtime.whitelist'
    _description = 'Test Model with Tracked Transitions Whitelist'
    _inherit = 'state.leadtime.mixin'

    name = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')

    _tracked_transitions = [('approved', 'done')]


class TestLeadtimeExactExclusionModel(models.TransientModel):
    _name = 'test.leadtime.exact_exclusion'
    _description = 'Test Model with Specific Pair Exclusion'
    _inherit = 'state.leadtime.mixin'

    name = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')

    _excluded_transitions = [('draft', 'approved')]


@tagged('post_install', '-at_install')
class TestStateLeadtimeMixin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for model_class in (
            TestLeadtimeModel,
            TestLeadtimeExclusionModel,
            TestLeadtimeWhitelistModel,
            TestLeadtimeExactExclusionModel,
        ):
            model_class._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            [
                'test.leadtime.model',
                'test.leadtime.exclusion',
                'test.leadtime.whitelist',
                'test.leadtime.exact_exclusion',
            ],
            {'module': 'agx_leadtime'},
        )
        cls.Model = cls.env['test.leadtime.model']
        cls.ExclusionModel = cls.env['test.leadtime.exclusion']
        cls.WhitelistModel = cls.env['test.leadtime.whitelist']
        cls.ExactExclusionModel = cls.env['test.leadtime.exact_exclusion']

    def _get_logs(self, record):
        return self.env['state.leadtime.log'].search([
            ('res_model', '=', record._name),
            ('res_id', '=', record.id),
        ])

    # --- create() ---

    def test_create_sets_state_entry_date(self):
        record = self.Model.create({'name': 'Test'})
        self.assertIsNotNone(record.state_entry_date)

    def test_create_preserves_provided_entry_date(self):
        ts = fields.Datetime.from_string('2024-01-01 10:00:00')
        record = self.Model.create({'name': 'Test', 'state_entry_date': ts})
        self.assertEqual(record.state_entry_date, ts)

    # --- write() state change ---

    def test_state_change_creates_log(self):
        record = self.Model.create({'name': 'Test'})
        record.write({'state': 'approved'})
        logs = self._get_logs(record)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.from_state, 'draft')
        self.assertEqual(logs.to_state, 'approved')

    def test_same_state_write_creates_no_log(self):
        record = self.Model.create({'name': 'Test'})
        record.write({'state': 'draft'})
        self.assertEqual(len(self._get_logs(record)), 0)

    def test_non_state_write_creates_no_log(self):
        record = self.Model.create({'name': 'Test'})
        record.write({'name': 'Updated'})
        self.assertEqual(len(self._get_logs(record)), 0)

    def test_multiple_transitions_create_multiple_logs(self):
        record = self.Model.create({'name': 'Test'})
        record.write({'state': 'approved'})
        record.write({'state': 'done'})
        logs = self._get_logs(record)
        self.assertEqual(len(logs), 2)

    # --- Bug B regression: transition_date synced with duration anchor ---

    def test_transition_date_consistent_with_duration(self):
        record = self.Model.create({'name': 'Test'})
        entry_date_before = record.state_entry_date
        record.write({'state': 'approved'})
        log = self._get_logs(record)
        self.assertEqual(len(log), 1)
        expected = (
            (log.transition_date - entry_date_before).total_seconds() / 60
            if entry_date_before else 0.0
        )
        # Allow < 1 second floating point drift
        self.assertAlmostEqual(log.duration_minutes, expected, delta=0.02)

    # --- _excluded_transitions blacklist ---

    def test_excluded_wildcard_to_state_blocks_log(self):
        record = self.ExclusionModel.create({'name': 'Test'})
        record.write({'state': 'rejected'})
        self.assertEqual(len(self._get_logs(record)), 0)

    def test_excluded_does_not_block_other_transitions(self):
        record = self.ExclusionModel.create({'name': 'Test'})
        record.write({'state': 'approved'})
        logs = self._get_logs(record)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.to_state, 'approved')

    # --- _tracked_transitions whitelist ---

    def test_whitelist_blocks_untracked_transition(self):
        record = self.WhitelistModel.create({'name': 'Test'})
        record.write({'state': 'approved'})
        self.assertEqual(len(self._get_logs(record)), 0)

    def test_whitelist_allows_tracked_transition(self):
        record = self.WhitelistModel.create({'name': 'Test', 'state': 'approved'})
        record.write({'state': 'done'})
        logs = self._get_logs(record)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.from_state, 'approved')
        self.assertEqual(logs.to_state, 'done')

    # --- state_entry_date lifecycle ---

    def test_state_entry_date_updated_after_transition(self):
        """state_entry_date advances to the moment of each state change."""
        past = fields.Datetime.from_string('2024-01-01 00:00:00')
        record = self.Model.create({'name': 'Test', 'state_entry_date': past})
        record.write({'state': 'approved'})
        self.assertGreater(record.state_entry_date, past)

    def test_duration_calculated_from_state_entry_date(self):
        """Log duration equals elapsed time from state_entry_date to transition."""
        fixed_entry = fields.Datetime.from_string('2020-01-01 00:00:00')
        record = self.Model.create({'name': 'Test', 'state_entry_date': fixed_entry})
        record.write({'state': 'approved'})
        log = self._get_logs(record)
        expected_minutes = (log.transition_date - fixed_entry).total_seconds() / 60
        self.assertAlmostEqual(log.duration_minutes, expected_minutes, delta=0.1)

    def test_state_entry_date_resets_between_transitions(self):
        """Each transition records duration from the previous state's entry, not creation."""
        early = fields.Datetime.from_string('2020-01-01 00:00:00')
        record = self.Model.create({'name': 'Test', 'state_entry_date': early})
        record.write({'state': 'approved'})
        date_after_first = record.state_entry_date

        record.write({'state': 'done'})
        logs = self._get_logs(record).sorted('transition_date')
        self.assertEqual(len(logs), 2)

        log_done = logs[-1]
        expected = (log_done.transition_date - date_after_first).total_seconds() / 60
        self.assertAlmostEqual(log_done.duration_minutes, expected, delta=0.1)

    # --- _excluded_transitions specific pair (non-wildcard) ---

    def test_excluded_specific_pair_blocks_matching_transition(self):
        """A specific (from, to) exclusion blocks only that exact pair."""
        record = self.ExactExclusionModel.create({'name': 'Test'})
        record.write({'state': 'approved'})  # ('draft', 'approved') excluded → no log
        self.assertEqual(len(self._get_logs(record)), 0)

        record.write({'state': 'done'})      # ('approved', 'done') not excluded → log created
        self.assertEqual(len(self._get_logs(record)), 1)
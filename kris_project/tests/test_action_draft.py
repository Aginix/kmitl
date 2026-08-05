from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import KrisProjectCommon


@tagged("post_install", "-at_install")
class TestKrisProjectActionDraft(KrisProjectCommon):
    """Guardrails and state coverage for kris.project.action_draft."""

    def _project_in_state(self, state):
        p = self._make_project()
        p.state = state
        return p

    def test_reset_from_cancel(self):
        p = self._project_in_state("cancel")
        p.action_draft()
        self.assertEqual(p.state, "draft")

    def test_reset_from_in_progress(self):
        p = self._project_in_state("in_progress")
        p.action_draft()
        self.assertEqual(p.state, "draft")

    def test_reset_from_done(self):
        p = self._project_in_state("done")
        p.action_draft()
        self.assertEqual(p.state, "draft")

    def test_reset_from_terminated(self):
        p = self._project_in_state("terminated")
        p.action_draft()
        self.assertEqual(p.state, "draft")

    def test_reset_from_conditional_close(self):
        p = self._project_in_state("conditional_close")
        p.action_draft()
        self.assertEqual(p.state, "draft")

    def test_reset_clears_exception_flags(self):
        p = self._project_in_state("done")
        p.ignore_exception = True
        p.action_draft()
        self.assertFalse(p.ignore_exception)
        self.assertFalse(p.main_exception_id)
        self.assertFalse(p.exception_ids)

    def test_reset_from_draft_raises(self):
        p = self._make_project()
        with self.assertRaises(UserError):
            p.action_draft()

    def test_reset_from_suspended_raises(self):
        p = self._project_in_state("suspended")
        with self.assertRaises(UserError):
            p.action_draft()

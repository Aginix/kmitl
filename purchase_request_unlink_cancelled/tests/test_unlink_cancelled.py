from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestUnlinkCancelled(TransactionCase):
    def _can_be_deleted(self, state):
        return self.env["purchase.request"].new({"state": state})._can_be_deleted()

    def test_draft_can_be_deleted(self):
        self.assertTrue(self._can_be_deleted("draft"))

    def test_cancelled_can_be_deleted(self):
        self.assertTrue(self._can_be_deleted("cancelled"))

    def test_other_states_cannot_be_deleted(self):
        for state in ("to_approve", "approved", "rejected", "done"):
            self.assertFalse(self._can_be_deleted(state), state)

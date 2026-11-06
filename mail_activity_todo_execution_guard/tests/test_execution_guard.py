from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

REQUEST = "odoo.addons.mail_activity_todo_execution_guard.models.mail_activity.request"


def _rpc(method):
    """A web-client request whose top-level call is mail.activity.<method>."""
    return patch(
        REQUEST, SimpleNamespace(params={"model": "mail.activity", "method": method})
    )


@tagged("post_install", "-at_install")
class TestExecutionGuard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, login="exec_guard_user", groups="base.group_user"
        )
        cls.admin = new_test_user(
            cls.env,
            login="exec_guard_admin",
            groups="base.group_user,base.group_system",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Anchor"})
        Type = cls.env["mail.activity.type"]
        cls.type_exec = Type.create({"name": "Exec", "todo_category": "execution"})
        cls.type_ack = Type.create({"name": "Ack", "todo_category": "acknowledgement"})

    def _activity(self, activity_type):
        return self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("res.partner"),
                "res_id": self.partner.id,
                "activity_type_id": activity_type.id,
                "user_id": self.user.id,
            }
        )

    def test_mark_done_from_client_blocked(self):
        act = self._activity(self.type_exec)
        for method in (
            "action_feedback",
            "action_done",
            "action_feedback_schedule_next",
        ):
            with _rpc(method), self.assertRaises(UserError):
                getattr(act.with_user(self.user), method)()
        self.assertTrue(act.exists())

    def test_cancel_from_client_blocked(self):
        act = self._activity(self.type_exec)
        with _rpc("unlink"), self.assertRaises(UserError):
            act.with_user(self.user).unlink()
        self.assertTrue(act.exists())

    def test_admin_may_close(self):
        act = self._activity(self.type_exec)
        with _rpc("action_feedback"):
            act.with_user(self.admin).action_feedback()
        self.assertFalse(act.exists())

    def test_business_path_closes_and_logs(self):
        """Source-model RPC (or no request at all) closes the Todo as before."""
        act = self._activity(self.type_exec)
        with patch(
            REQUEST,
            SimpleNamespace(params={"model": "res.partner", "method": "action_x"}),
        ):
            act.with_user(self.user).action_feedback()
        self.assertFalse(act.exists())
        self.assertTrue(
            self.env["todo.log"].search([("activity_type_id", "=", self.type_exec.id)])
        )

    def test_acknowledgement_unaffected(self):
        act = self._activity(self.type_ack)
        with _rpc("action_feedback"):
            act.with_user(self.user).action_feedback()
        self.assertFalse(act.exists())

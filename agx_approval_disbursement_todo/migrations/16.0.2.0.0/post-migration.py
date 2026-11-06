# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import SUPERUSER_ID, api

# The hand-off of the request to finance is gone (agx_approval ADR-0010): its
# automations and To-Do types are noupdate data, so they are removed here.
RETIRED = [
    "automation_notify_record_actual",
    "automation_notify_finance_return",
    "automation_clear_record_actual",
    "automation_notify_finance_verify",
    "automation_clear_finance_verify",
    "automation_notify_billed_fyi",
]
RETIRED_ACTIVITY_TYPES = ["mail_activity_record_actual", "mail_activity_finance_verify"]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for name in RETIRED:
        record = env.ref("agx_approval_disbursement_todo.%s" % name, False)
        if record:
            action = record.action_server_id
            record.unlink()
            if action.exists():
                action.unlink()
    for name in RETIRED_ACTIVITY_TYPES:
        activity_type = env.ref("agx_approval_disbursement_todo.%s" % name, False)
        if activity_type:
            env["mail.activity"].search(
                [("activity_type_id", "=", activity_type.id)]
            ).unlink()
            activity_type.unlink()

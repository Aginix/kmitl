from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The จองงบประมาณ Todo moved from to_verify to the new to_commit step
    (agx_approval ADR-0008). The automations are noupdate, so re-point the
    existing records here instead of relying on the XML reload."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    notify = env.ref(
        "agx_approval_budget_todo.automation_notify_reserve_budget",
        raise_if_not_found=False,
    )
    if notify:
        notify.write(
            {
                "name": "คำขออนุมัติ: แจ้งเจ้าหน้าที่จองงบประมาณเมื่อเข้าสถานะ"
                "รอยืนยันงบประมาณ",
                "filter_pre_domain": "[('state', '!=', 'to_commit')]",
                "filter_domain": "[('state', '=', 'to_commit')]",
                "code": (notify.code or "").replace(
                    "รอตรวจสอบและจองงบประมาณ", "รอยืนยันงบประมาณ"
                ),
            }
        )
    clear = env.ref(
        "agx_approval_budget_todo.automation_clear_reserve_budget",
        raise_if_not_found=False,
    )
    if clear:
        clear.write(
            {
                "name": "คำขออนุมัติ: ล้าง Todo จองงบประมาณเมื่อออกจากสถานะ"
                "รอยืนยันงบประมาณ",
                "filter_pre_domain": "[('state', '=', 'to_commit')]",
                "filter_domain": "[('state', '!=', 'to_commit')]",
            }
        )
    # Requests already waiting at to_verify carry a Todo scheduled under the old
    # trigger. Drop it: the notify automation re-creates it once they reach
    # to_commit, and keeping it would leave a duplicate there.
    waiting = env["approval.request"].search([("state", "=", "to_verify")])
    waiting.activity_unlink(["agx_approval_budget_todo.mail_activity_reserve_budget"])

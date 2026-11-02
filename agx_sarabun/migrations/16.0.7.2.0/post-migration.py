from odoo import SUPERUSER_ID, api

RETIRED_TYPES = (
    "agx_sarabun.mail_activity_sarabun_action",
    "agx_sarabun.mail_activity_sarabun_ack",
)


def migrate(cr, version):
    """One activity type per verb (ADR-0020): give every verb its own type, move the
    open awaiting-action activities off the two retired generic types onto their
    step's verb type, then archive those two (kept for todo.log history).

    The re-point is raw SQL on purpose: it must not recompute the stored
    ``todo_category`` of open Todos, which keep the category they were raised with.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["sarabun.verb"].with_context(active_test=False).search([])._sync_activity_type()
    old_types = env["mail.activity.type"]
    for xmlid in RETIRED_TYPES:
        old_types |= env.ref(xmlid, raise_if_not_found=False) or old_types
    if not old_types:
        return
    env.flush_all()
    cr.execute(
        """
        UPDATE mail_activity a
           SET activity_type_id = v.activity_type_id
          FROM sarabun_routing_step_activity l
          JOIN sarabun_routing_step s ON s.id = l.step_id
          JOIN sarabun_verb v ON v.id = s.verb
         WHERE l.activity_id = a.id
           AND v.activity_type_id IS NOT NULL
           AND a.activity_type_id IN %s
        """,
        [tuple(old_types.ids)],
    )
    env.invalidate_all()
    old_types.write({"active": False})

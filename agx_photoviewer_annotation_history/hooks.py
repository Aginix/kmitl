from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Start the History with the annotations made before it was installed:
    one Change per author and day, adding what is on the layer now (ADR-0001).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    annotations = env["ir.attachment.annotation"].search([])
    env["ir.attachment.annotation.event"].create(
        [
            dict(
                annotation._history_event_values(
                    "add", after=annotation._history_snapshot()
                ),
                session_key="initial-%s-%s"
                % (annotation.create_uid.id, annotation.create_date.date()),
                user_id=annotation.create_uid.id or SUPERUSER_ID,
                date=annotation.create_date,
            )
            for annotation in annotations
        ]
    )

from odoo import SUPERUSER_ID, api


def pre_init_hook(cr):
    """Create the column empty, so Odoo does not fill existing rows with the
    field default (the installer's OU) and the backfill below sees them."""
    cr.execute(
        "ALTER TABLE sarabun_document ADD COLUMN IF NOT EXISTS operating_unit_id int4"
    )


def post_init_hook(cr, registry):
    """Backfill the OU of existing หนังสือ: from the origin record when it has an
    ``operating_unit_id``, else the sender's default OU."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        "SELECT DISTINCT origin_model FROM sarabun_document "
        "WHERE operating_unit_id IS NULL AND origin_model IS NOT NULL"
    )
    for (model_name,) in cr.fetchall():
        model = env.get(model_name)
        field = model is not None and model._fields.get("operating_unit_id")
        if not (field and field.store and field.comodel_name == "operating.unit"):
            continue
        cr.execute(
            f"""
            UPDATE sarabun_document d
               SET operating_unit_id = o.operating_unit_id
              FROM "{model._table}" o
             WHERE d.operating_unit_id IS NULL
               AND d.origin_model = %s
               AND d.origin_res_id = o.id
            """,
            (model_name,),
        )
    cr.execute(
        """
        UPDATE sarabun_document d
           SET operating_unit_id = u.default_operating_unit_id
          FROM res_users u
         WHERE d.operating_unit_id IS NULL
           AND d.sender_user_id = u.id
        """
    )

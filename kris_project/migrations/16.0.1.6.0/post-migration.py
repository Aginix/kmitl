def migrate(cr, version):
    """Backfill unrevisioned_name when base_revision is added to an existing
    deployment. post_init_hook only runs on a fresh install, so an upgrade of
    the already-installed module needs this to seed the revision baseline.
    """
    cr.execute(
        "UPDATE kris_project SET unrevisioned_name = name "
        "WHERE unrevisioned_name IS NULL"
    )

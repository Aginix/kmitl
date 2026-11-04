def migrate(cr, version):
    # Own Projects used to imply Viewer, which stamped Viewer membership onto
    # every project user; drop the link and those memberships so Viewer's
    # read-all reaches only real viewers. Users still granted Viewer by another
    # group (e.g. a role) keep it; Officers/Managers regain it on data load.
    cr.execute(
        """
        SELECT
            (SELECT res_id FROM ir_model_data
             WHERE module = 'kmitl_project'
               AND name = 'group_kmitl_project_user'),
            (SELECT res_id FROM ir_model_data
             WHERE module = 'kmitl_project_viewer'
               AND name = 'group_kmitl_project_viewer')
        """
    )
    own_id, viewer_id = cr.fetchone()
    cr.execute(
        "DELETE FROM res_groups_implied_rel WHERE gid = %s AND hid = %s",
        (own_id, viewer_id),
    )
    cr.execute(
        """
        WITH RECURSIVE implying(gid) AS (
            SELECT gid FROM res_groups_implied_rel WHERE hid = %(viewer)s
            UNION
            SELECT r.gid FROM res_groups_implied_rel r
            JOIN implying i ON r.hid = i.gid
        )
        DELETE FROM res_groups_users_rel r
        WHERE r.gid = %(viewer)s
          AND r.uid IN (
              SELECT uid FROM res_groups_users_rel WHERE gid = %(own)s
          )
          AND r.uid NOT IN (
              SELECT u.uid FROM res_groups_users_rel u
              JOIN implying i ON u.gid = i.gid
          )
        """,
        {"own": own_id, "viewer": viewer_id},
    )

def migrate(cr, version):
    # Own Projects used to imply Viewer, which stamped Viewer membership onto
    # every project user; drop the link and those memberships before Viewer
    # starts granting read-all. Officers/Managers regain Viewer on data load.
    cr.execute(
        """
        WITH g AS (
            SELECT
                (SELECT res_id FROM ir_model_data
                 WHERE module = 'kmitl_project'
                   AND name = 'group_kmitl_project_user') AS own_id,
                (SELECT res_id FROM ir_model_data
                 WHERE module = 'kmitl_project_viewer'
                   AND name = 'group_kmitl_project_viewer') AS viewer_id
        ), del_link AS (
            DELETE FROM res_groups_implied_rel r
            USING g
            WHERE r.gid = g.own_id AND r.hid = g.viewer_id
        )
        DELETE FROM res_groups_users_rel r
        USING g
        WHERE r.gid = g.viewer_id
          AND r.uid IN (
              SELECT uid FROM res_groups_users_rel WHERE gid = g.own_id
          )
        """
    )

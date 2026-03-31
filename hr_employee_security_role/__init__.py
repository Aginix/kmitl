from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group_hr_user = env.ref("hr.group_hr_user")
    group_hr_central_user = env.ref("hr_employee_security_role.group_hr_central_user")
    for i in group_hr_user.users:
        group_hr_central_user.write({"users": [(4, i.id)]})


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group_hr_user = env.ref("hr.group_hr_user")
    group_hr_central_user = env.ref("hr_employee_security_role.group_hr_central_user")
    group_hr_manager = env.ref("hr.group_hr_manager")

    # 1. Depromote hr_user and not in hr_central_user to user
    hr_central_user_ids = list(map(lambda user: user.id, group_hr_central_user.users))
    hr_user_ids = list(map(lambda user: user.id, group_hr_user.users))
    for user_id in hr_user_ids:
        if user_id not in hr_central_user_ids:
            group_hr_user.write({"users": [(3, user_id)]})

    # 2. Remove all users in group_hr_central
    for user_id in hr_central_user_ids:
        group_hr_central_user.write({"users": [(3, user_id)]})

    # 3. Reset access right to default HR
    env.ref("hr.access_hr_employee_user").write(
        {
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": True,
        }
    )

    # 3.1 Remove customized access right
    env.ref("hr.access_hr_central_user").unlink()

    # 3.2 Reset to default config
    env.ref("hr.access_hr_work_location_manager").write({"group_id": group_hr_user.id})
    env.ref("hr.access_hr_departure_reason").write(
        {
            "group_id": group_hr_user.id,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": True,
        }
    )

    # 3.3 Remove customized access right
    env.ref("hr.access_hr_departure_reason_manager").unlink()

    # 4. Remove rules
    env.ref("hr_employee_security_role.hr_employee_department_officer_rule").unlink()
    env.ref("hr_employee_security_role.hr_employee_central_officer_rule").unlink()

    # 5. Unlink group_hr_central_user from group_hr_manager
    group_hr_manager.write({"implied_ids": [(3, group_hr_central_user)]})

    # 6. Reset group_hr_user to default config
    group_hr_user.write(
        {
            "name": "Officer : Manage all employees",
            "comment": "This group is used to give access to all employees to manage all employees",
        }
    )

    # 7. Remove customized group_hr_central_user
    env.ref("hr_employee_security_role.group_hr_central_user").unlink()

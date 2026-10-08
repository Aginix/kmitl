from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase


class KmitlProjectCoordinatorCommon(TransactionCase):
    """A project in OU A created by ``creator`` (OU A), led by ``manager_user``
    (OU B) and coordinated by ``coordinator`` (OU B); ``stranger`` (OU A) is a
    project user who owns nothing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        company = env.company
        cls.ou_a = env["operating.unit"].create(
            {"name": "Coord OU A", "code": "COA", "partner_id": company.partner_id.id}
        )
        cls.ou_b = env["operating.unit"].create(
            {"name": "Coord OU B", "code": "COB", "partner_id": company.partner_id.id}
        )
        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-COORD",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": company.id,
                }
            )
        group_user = env.ref("kmitl_project.group_kmitl_project_user")

        def _user(login, ou):
            user = env["res.users"].create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.com" % login,
                    "groups_id": [Command.set([group_user.id])],
                }
            )
            user.assigned_operating_unit_ids = ou
            user.default_operating_unit_id = ou
            return user

        cls.creator = _user("kp_creator", cls.ou_a)
        cls.coordinator = _user("kp_coordinator", cls.ou_b)
        cls.manager_user = _user("kp_manager", cls.ou_b)
        cls.stranger = _user("kp_stranger", cls.ou_a)
        cls.manager = env["hr.employee"].create(
            {"name": "kp_manager", "user_id": cls.manager_user.id}
        )

        cls.project = (
            env["kmitl.project"]
            .with_user(cls.creator)
            .create(
                {
                    "name": "Coordinated Project",
                    "account_fiscal_year_id": cls.fiscal_year.id,
                    "operating_unit_id": cls.ou_a.id,
                    "manager_id": cls.manager.id,
                    "coordinator_id": cls.coordinator.id,
                }
            )
            .sudo()
        )
        cls.subtype = env.ref("kmitl_project_coordinator.mt_kmitl_project_state")

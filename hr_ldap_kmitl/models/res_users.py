import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _kmitl_link_employee_by_email(self):
        """Link each user to an existing employee whose ``work_email`` matches
        the user's login (the full email used to log in).

        This is the missing piece that ``auth_ldap`` does not provide: when a
        user is auto-created on first LDAP login, the new ``res.users`` is not
        connected to the employee record that already exists in the directory.

        Best-effort by design: it must **never raise**. It runs from an
        ``on_create`` automation inside the LDAP login transaction, so any
        exception here would roll back the ``create`` and block the user's very
        first login. A failure is logged instead and can be recovered later by
        the backfill server action.
        """
        Employee = self.env["hr.employee"].sudo()
        for user in self:
            # Skip portal/public users and users without a login.
            if user.share or not user.login:
                continue
            login = user.login.strip().lower()
            try:
                # Coarse, case-insensitive narrowing at the DB level, then an
                # exact Python compare so ``_`` / ``%`` in an address cannot
                # cause a wrong or ambiguous match (``=ilike`` treats them as
                # wildcards).
                candidates = Employee.search(
                    [
                        ("user_id", "=", False),
                        ("work_email", "=ilike", login),
                    ],
                    limit=10,
                )
                employee = candidates.filtered(
                    lambda e: (e.work_email or "").strip().lower() == login
                )[:1]
                if employee:
                    employee.user_id = user.id
            except Exception:  # noqa: BLE001 - linking must not break login
                _logger.exception(
                    "hr_ldap_kmitl: could not link user %s to an employee",
                    user.login,
                )

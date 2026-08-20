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
                if not employee:
                    continue
                # Reuse the employee's existing work contact so we do not leave
                # the freshly auto-created user partner orphaned (prod already
                # carries many partners on employees).
                self._kmitl_reuse_employee_partner(user, employee)
                employee.user_id = user.id
            except Exception:  # noqa: BLE001 - linking must not break login
                _logger.exception(
                    "hr_ldap_kmitl: could not link user %s to an employee",
                    user.login,
                )

    def _kmitl_reuse_employee_partner(self, user, employee):
        """Repoint ``user`` at the employee's existing ``work_contact_id`` and
        drop the partner that user-creation just auto-generated.

        Without this, linking runs ``hr`` ``_sync_user`` which overwrites the
        employee's ``work_contact_id`` with the user's partner, orphaning the
        real contact and leaving two partner records for one person. Only
        ``work_contact_id`` is reused (the professional identity); a private
        ``address_home_id`` is a different role and is intentionally left as is.
        """
        existing_partner = employee.work_contact_id
        stray_partner = user.partner_id
        if not existing_partner or existing_partner == stray_partner:
            return
        # Move the FK first (partner_id is ondelete='restrict'), then remove the
        # now-unreferenced stray partner.
        user.partner_id = existing_partner.id
        try:
            stray_partner.sudo().unlink()
        except Exception:  # noqa: BLE001 - keep going even if it cannot be deleted
            _logger.warning(
                "hr_ldap_kmitl: could not delete stray partner %s, archiving it",
                stray_partner.id,
            )
            stray_partner.sudo().write({"active": False})

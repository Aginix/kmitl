import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


UPDATE_PARTNER_FIELDS = [
    "firstname",
    "middlename",
    "lastname",
    "user_id",
    "address_home_id",
]

NO_NAME_TEXT = "Untitled"


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _get_name(self, firstname, middlename, lastname):
        return " ".join(p for p in (firstname, middlename, lastname) if p)

    @api.onchange("firstname", "lastname", "middlename")
    def _onchange_firstname_middlename_lastname(self):
        if self.firstname or self.middlename or self.lastname:
            self.name = self._get_name(self.firstname, self.middlename, self.lastname)
        elif not self.firstname and not self.middlename and not self.lastname:
            self.name = NO_NAME_TEXT

    @api.model
    def _is_partner_fullname_installed(self):
        return bool(
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "partner_firstname"), ("state", "=", "installed")])
        )

    @api.model_create_multi
    def create(self, vals):
        for data in vals:
            self._prepare_vals_on_create_firstname_middle_lastname(data)
        res = super().create(vals)
        if self._is_partner_fullname_installed():
            res._update_partner_fullname()
        return res

    def write(self, vals):
        for employee in self:
            employee._prepare_vals_on_write_firstname_middlename_lastname(vals)
        res = super().write(vals)
        if self._is_partner_fullname_installed() and set(vals).intersection(
            UPDATE_PARTNER_FIELDS
        ):
            self._update_partner_fullname()
        return res

    def _prepare_vals_on_create_firstname_middle_lastname(self, vals):
        if vals.get("firstname") or vals.get("middlename") or vals.get("lastname"):
            vals["name"] = self._get_name(
                vals.get("firstname"), vals.get("middlename"), vals.get("lastname")
            )
        elif vals.get("name"):
            vals["firstname"] = self.split_name(vals["name"])["firstname"]
            vals["middlename"] = self.split_name(vals["name"])["middlename"]
            vals["lastname"] = self.split_name(vals["name"])["lastname"]
        else:
            vals["name"] = NO_NAME_TEXT

    def _prepare_vals_on_write_firstname_middlename_lastname(self, vals):
        if "firstname" in vals or "middlename" in vals or "lastname" in vals:
            if "firstname" in vals:
                firstname = vals.get("firstname")
            else:
                firstname = self.firstname

            if "middlename" in vals:
                middlename = vals.get("middlename")
            else:
                middlename = self.middlename

            if "lastname" in vals:
                lastname = vals.get("lastname")
            else:
                lastname = self.lastname

            vals["name"] = self._get_name(firstname, middlename, lastname)

        elif vals.get("name"):
            if vals.get("name") == NO_NAME_TEXT:
                vals["name"] = NO_NAME_TEXT
            else:
                vals["firstname"] = self.split_name(vals["name"])["firstname"]
                vals["middlename"] = self.split_name(vals["name"])["middlename"]
                vals["lastname"] = self.split_name(vals["name"])["lastname"]
        else:
            if self.name and self.name != NO_NAME_TEXT:
                return
            else:
                vals["name"] = NO_NAME_TEXT

    @api.model
    def _get_whitespace_cleaned_name(self, name):
        """Remove redundant whitespace from :param:`name`.
        Removes leading, trailing and duplicated whitespace.
        """
        try:
            name = " ".join(name.split()) if name else name
        except UnicodeDecodeError:
            name = " ".join(name.decode("utf-8").split()) if name else name

        return name

    @api.model
    def _get_inverse_name(self, name):
        """Compute the inverted name.
        This method can be easily overriden by other submodules.
        You can also override this method to change the order of name's
        attributes
        When this method is called, :attr:`~.name` already has unified and
        trimmed whitespace.
        """

        name = self._get_whitespace_cleaned_name(name)
        parts = name.split(" ")
        if len(parts) == 1:
            return {"firstname": parts[0], "middlename": False, "lastname": False}
        if len(parts) == 2:
            return {"firstname": parts[0], "middlename": False, "lastname": parts[1]}
        if len(parts) >= 3:
            return {
                "firstname": parts[0],
                "middlename": parts[1],
                "lastname": " ".join(parts[2:]),
            }

    @api.model
    def split_name(self, name):
        clean_name = " ".join(name.split(None)) if name else name
        return self._get_inverse_name(clean_name)

    def _inverse_name(self):
        """Try to revert the effect of :meth:`._compute_name`."""
        for record in self:
            parts = self._get_inverse_name(record.name)
            record.firstname = parts["firstname"]
            record.middlename = parts["middlename"]
            record.lastname = parts["lastname"]

    @api.model
    def _install_employee_fullname(self):
        """Save names correctly in the database.
        Before installing the module, field ``name`` contains all full names.
        When installing it, this method parses those names and saves them
        correctly into the database. This can be called later too if needed.
        """

        records = self.search(
            [
                ("firstname", "=", False),
                ("middlename", "=", False),
                ("lastname", "=", False),
            ]
        )

        records._inverse_name()
        _logger.info("%d employees updated installing module.", len(records))

    def _update_partner_fullname(self):
        for employee in self:
            partners = employee.mapped("user_id.partner_id")
            partners |= employee.mapped("address_home_id")
            partners.write(
                {
                    "firstname": employee.firstname,
                    "middlename": employee.middlename,
                    "lastname": employee.lastname,
                }
            )

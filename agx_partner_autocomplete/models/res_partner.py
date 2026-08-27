# -*- coding: utf-8 -*-
from odoo import _, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_partner_autocomplete_info(self):
        """Display payload for the ``partner_autocomplete`` m2o widget.

        One dict per record: identity plus the label/value rows the dropdown
        renders verbatim, so labels, translations and formatting all stay
        server-side and the widget stays dumb. The partner "type" is a
        dedicated hook (:meth:`_partner_autocomplete_type`) so a bridge module
        can swap the generic Individual/Company classification for its own
        without touching the widget or the rest of the payload.
        """
        return [record._partner_autocomplete_info() for record in self]

    def _partner_autocomplete_info(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": (self.display_name or self.name or "").split("\n")[0],
            "is_company": self.is_company,
            "type": self._partner_autocomplete_type(),
            "rows": self._partner_autocomplete_rows(),
        }

    def _partner_autocomplete_type(self):
        """Short classification shown on the option badge. Overridable."""
        self.ensure_one()
        return dict(
            self._fields["company_type"]._description_selection(self.env)
        ).get(self.company_type, "")

    def _partner_autocomplete_rows(self):
        """(label, value, icon) rows — only the ones that carry a value, so an
        empty contact shows just its name and type rather than blank rows."""
        self.ensure_one()
        rows = []
        if self.vat:
            rows.append(
                {"label": _("VAT"), "value": self.vat, "icon": "fa-id-card-o"}
            )
        address = self._partner_autocomplete_address()
        if address:
            rows.append(
                {"label": _("Address"), "value": address, "icon": "fa-map-marker"}
            )
        if self.email:
            rows.append(
                {"label": _("Email"), "value": self.email, "icon": "fa-envelope-o"}
            )
        phone = self.phone or self.mobile
        if phone:
            rows.append({"label": _("Phone"), "value": phone, "icon": "fa-phone"})
        return rows

    def _partner_autocomplete_address(self):
        """One-line address from the standard address parts, empties dropped."""
        self.ensure_one()
        parts = [
            self.street,
            self.street2,
            self.city,
            self.state_id.name,
            self.zip,
            self.country_id.name,
        ]
        return ", ".join(part for part in parts if part)

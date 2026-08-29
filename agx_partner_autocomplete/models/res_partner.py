# -*- coding: utf-8 -*-
from odoo import _, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_partner_autocomplete_info(self):
        """Display payload for the ``agx_partner_many2one`` m2o widget.

        One dict per record: identity plus the label/value rows the dropdown
        renders verbatim, so labels, translations and formatting all stay
        server-side and the widget stays dumb. Rows and subtitle parts each
        carry a ``key`` so the widget's ``show_<key>`` display options can
        toggle them on/off without any change here — new keys are toggleable
        for free the moment a hook starts tagging them. The partner "type" is
        a dedicated hook (:meth:`_partner_autocomplete_type`) so a bridge
        module can swap the generic Individual/Company classification for its
        own without touching the widget or the rest of the payload.
        """
        return [record._partner_autocomplete_info() for record in self]

    def _partner_autocomplete_info(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": (self.display_name or self.name or "").split("\n")[0],
            "is_company": self.is_company,
            "type": self._partner_autocomplete_type(),
            "subtitle_parts": self._partner_autocomplete_subtitle_parts(),
            "rows": self._partner_autocomplete_rows(),
        }

    def _partner_autocomplete_type(self):
        """Short classification shown on the option badge. Overridable."""
        self.ensure_one()
        return dict(
            self._fields["company_type"]._description_selection(self.env)
        ).get(self.company_type, "")

    def _partner_autocomplete_subtitle_parts(self):
        """Ordered (key, value) parts for the compact subtitle shown under a
        selected value. Reuses the same overridable type hook as the badge, so
        a bridge's classification flows here too. The widget filters by
        show_<key> and joins what's left with " · "."""
        self.ensure_one()
        parts = []
        type_label = self._partner_autocomplete_type()
        if type_label:
            parts.append({"key": "type", "value": type_label})
        if self.vat:
            parts.append({"key": "vat", "value": self.vat})
        locality = self.city or self.country_id.name
        if locality:
            parts.append({"key": "address", "value": locality})
        return parts

    def _partner_autocomplete_rows(self):
        """(key, label, value, icon) rows — only the ones that carry a value,
        so an empty contact shows just its name and type rather than blank
        rows. The widget filters rows by show_<key>."""
        self.ensure_one()
        rows = []
        if self.vat:
            rows.append(
                {"key": "vat", "label": _("VAT"), "value": self.vat, "icon": "fa-id-card-o"}
            )
        address = self._partner_autocomplete_address()
        if address:
            rows.append(
                {"key": "address", "label": _("Address"), "value": address, "icon": "fa-map-marker"}
            )
        if self.email:
            rows.append(
                {"key": "email", "label": _("Email"), "value": self.email, "icon": "fa-envelope-o"}
            )
        phone = self.phone or self.mobile
        if phone:
            rows.append({"key": "phone", "label": _("Phone"), "value": phone, "icon": "fa-phone"})
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

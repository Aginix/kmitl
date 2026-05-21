from markupsafe import Markup

from odoo import api, models
from odoo.exceptions import MissingError


class ApplicantTrackedChild(models.AbstractModel):
    _name = "hr.applicant.tracked.child"
    _description = "Applicant Tracked Child Mixin"
    _inherit = "mail.thread"

    def _applicant_for_tracking(self):
        self.ensure_one()
        return self.applicant_id

    def _tracking_label(self):
        self.ensure_one()
        return self.display_name or self._description

    def _message_track(self, fields_iter, initial_values_dict):
        tracked_fields = self.fields_get(
            fields_iter, attributes=("string", "type", "selection", "currency_field")
        )
        for record in self:
            try:
                changes, tracking_value_ids = record._mail_track(
                    tracked_fields, initial_values_dict.get(record.id, {})
                )
            except MissingError:
                continue
            if not changes:
                continue
            try:
                applicant = record._applicant_for_tracking()
            except MissingError:
                continue
            if not applicant:
                continue
            applicant._message_log(
                body=Markup("<b>{}:</b>").format(record._tracking_label()),
                tracking_value_ids=tracking_value_ids,
            )
        return {}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            try:
                applicant = record._applicant_for_tracking()
            except MissingError:
                continue
            if not applicant:
                continue
            applicant._message_log(
                body=Markup("Added {}: <b>{}</b>").format(
                    self._description, record._tracking_label()
                )
            )
        return records

    def unlink(self):
        prior = []
        for record in self:
            try:
                applicant = record._applicant_for_tracking()
                label = record._tracking_label()
                prior.append((applicant, label))
            except MissingError:
                continue
        result = super().unlink()
        for applicant, label in prior:
            if not applicant:
                continue
            try:
                applicant._message_log(
                    body=Markup("Removed {}: <b>{}</b>").format(
                        self._description, label
                    )
                )
            except MissingError:
                pass
        return result

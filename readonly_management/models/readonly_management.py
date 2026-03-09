# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ReadonlyManagement(models.Model):
    """
    Central configuration for readonly field rules.

    Each record targets one model and defines which fields should be made
    readonly under what conditions. Rules are applied dynamically via
    get_view injection on the base model.
    """

    _name = "readonly.management"
    _description = "Readonly Management"
    _order = "name"

    name = fields.Char(string="Configuration Name", required=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        required=True,
        ondelete="cascade",
    )
    model_name = fields.Char(
        string="Model Technical Name",
        related="model_id.model",
        store=True,
        index=True,
    )
    field_ids = fields.One2many(
        "readonly.management.fields",
        "management_id",
        string="Field Rules",
    )
    apply_on_domain = fields.Char(
        string="Global Gate Condition",
        help=(
            "Odoo domain string. When set, this entire config activates only "
            "when this domain matches the record. "
            "Example: [('state', 'in', ['submit', 'to_verify'])]"
        ),
    )
    note = fields.Text(string="Notes")
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["ir.ui.view"].clear_caches()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.env["ir.ui.view"].clear_caches()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["ir.ui.view"].clear_caches()
        return result


class ReadonlyManagementFields(models.Model):
    """
    A single field rule within a ReadonlyManagement configuration.

    Supports an optional per-field domain condition AND-ed with the parent
    config's apply_on_domain gate.
    """

    _name = "readonly.management.fields"
    _description = "Readonly Management Field Rule"
    _order = "field_name"

    management_id = fields.Many2one(
        "readonly.management",
        string="Configuration",
        required=True,
        ondelete="cascade",
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Field",
        required=True,
        domain="[('model_id', '=', parent.model_id)]",
        ondelete="cascade",
    )
    field_name = fields.Char(
        string="Field Technical Name",
        related="field_id.name",
        store=True,
    )
    force_readonly = fields.Boolean(
        string="Always Readonly (no per-field condition)",
        default=False,
        help=(
            "When checked, this field is readonly purely based on the parent "
            "config's Global Gate Condition (or always if no gate is set). "
            "The Per-Field Condition is ignored."
        ),
    )
    domain = fields.Char(
        string="Per-Field Condition",
        help=(
            "Optional additional domain condition for this specific field. "
            "AND-ed with the parent config's Global Gate Condition. "
            "Ignored when 'Always Readonly' is checked."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["ir.ui.view"].clear_caches()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.env["ir.ui.view"].clear_caches()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["ir.ui.view"].clear_caches()
        return result

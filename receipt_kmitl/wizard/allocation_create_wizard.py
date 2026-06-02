# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AllocationCreateWizard(models.TransientModel):
    _name = "receipt.kmitl.allocation.wizard"
    _description = "Suspense Allocation Wizard"

    date = fields.Date(required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain=[("type", "=", "general")],
        default=lambda self: self.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        ).id,
    )
    note = fields.Text()
    line_ids = fields.One2many(
        "receipt.kmitl.allocation.wizard.line",
        "wizard_id",
        string="Allocation Lines",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if not active_ids:
            raise UserError(_("No receipts selected."))
        if active_model == "receipt.kmitl":
            receipts = self.env["receipt.kmitl"].browse(active_ids)
            receipt_lines = receipts.mapped("line_ids")
        elif active_model == "receipt.kmitl.line":
            receipt_lines = self.env["receipt.kmitl.line"].browse(active_ids)
        else:
            raise UserError(_("Invalid context for allocation wizard."))
        eligible = receipt_lines.filtered(
            lambda l: l.state == "deposited" and not l.allocation_line_id
        )
        if not eligible:
            raise UserError(
                _("No eligible receipt lines (must be deposited and unallocated).")
            )
        line_vals = []
        for rl in eligible:
            suggested = (
                rl.receipt_type_id.default_income_account_id
                or self.env["account.account"]
            )
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "receipt_line_id": rl.id,
                        "income_account_id": suggested.id or False,
                    },
                )
            )
        res["line_ids"] = line_vals
        return res

    def action_create_allocation(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Nothing to allocate."))
        for wl in self.line_ids:
            if not wl.income_account_id:
                raise ValidationError(
                    _("Choose an income account for every line.")
                )
        allocation = self.env["receipt.kmitl.allocation"].create(
            {
                "date": self.date,
                "journal_id": self.journal_id.id,
                "note": self.note,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "receipt_line_id": wl.receipt_line_id.id,
                            "income_account_id": wl.income_account_id.id,
                        },
                    )
                    for wl in self.line_ids
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Suspense Allocation"),
            "res_model": "receipt.kmitl.allocation",
            "view_mode": "form",
            "res_id": allocation.id,
        }


class AllocationCreateWizardLine(models.TransientModel):
    _name = "receipt.kmitl.allocation.wizard.line"
    _description = "Suspense Allocation Wizard Line"

    wizard_id = fields.Many2one(
        "receipt.kmitl.allocation.wizard",
        required=True,
        ondelete="cascade",
    )
    receipt_line_id = fields.Many2one(
        "receipt.kmitl.line",
        required=True,
        readonly=True,
    )
    receipt_id = fields.Many2one(
        related="receipt_line_id.receipt_id",
        store=False,
        readonly=True,
    )
    receipt_type_id = fields.Many2one(
        related="receipt_line_id.receipt_type_id",
        store=False,
        readonly=True,
    )
    suspense_account_id = fields.Many2one(
        related="receipt_line_id.suspense_account_id",
        store=False,
        readonly=True,
    )
    description = fields.Char(
        related="receipt_line_id.name",
        store=False,
        readonly=True,
    )
    amount = fields.Monetary(
        related="receipt_line_id.amount",
        store=False,
        readonly=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="receipt_line_id.currency_id",
        store=False,
        readonly=True,
    )
    income_account_id = fields.Many2one(
        "account.account",
        required=True,
        domain="[('deprecated', '=', False), ('account_type', '=', 'income')]",
    )

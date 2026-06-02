# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class SuspenseAllocationLine(models.Model):
    _name = "receipt.kmitl.allocation.line"
    _description = "Suspense Allocation Line"
    _order = "allocation_id, id"

    allocation_id = fields.Many2one(
        "receipt.kmitl.allocation",
        required=True,
        ondelete="cascade",
    )
    receipt_line_id = fields.Many2one(
        "receipt.kmitl.line",
        string="Receipt Line",
        required=True,
        domain="[('state', '=', 'deposited'), ('allocation_line_id', '=', False)]",
    )
    receipt_id = fields.Many2one(
        "receipt.kmitl",
        related="receipt_line_id.receipt_id",
        store=True,
        readonly=True,
    )
    receipt_type_id = fields.Many2one(
        "receipt.kmitl.type",
        related="receipt_line_id.receipt_type_id",
        store=True,
        readonly=True,
    )
    suspense_account_id = fields.Many2one(
        "account.account",
        related="receipt_line_id.suspense_account_id",
        store=True,
        readonly=True,
    )
    income_account_id = fields.Many2one(
        "account.account",
        string="Income Account",
        required=True,
        domain="[('deprecated', '=', False), ('account_type', '=', 'income')]",
    )
    analytic_distribution = fields.Json(
        related="receipt_line_id.analytic_distribution",
        store=True,
        readonly=True,
    )
    amount = fields.Monetary(
        related="receipt_line_id.amount",
        store=True,
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="receipt_line_id.currency_id",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "receipt_line_unique",
            "unique(receipt_line_id)",
            "A receipt line can only be allocated once.",
        ),
    ]

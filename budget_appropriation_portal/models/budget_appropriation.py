# -*- coding: utf-8 -*-
import logging

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    account_ids = fields.Many2many(
        "budget.account",
        compute="_compute_account_ids",
        context={"active_test": False},
        string="Budget Accounts",
        help="Budget accounts computed from budget account hierarchy.",
    )

    def open_record_url(self):
        if self.id:
            return {
                'type': 'ir.actions.act_url',
                'url': '/budget/budget_appropriation/%s' % (self.id),
                'target': 'new',
            }

    @api.depends("line_ids.account_id")
    def _compute_account_ids(self):
        for rec in self:
            all_account_ids = []
            for account_ids in rec.line_ids.mapped("account_ids"):
                all_account_ids += account_ids.mapped("id")
            for account_ids in rec.deduct_line_ids.mapped("account_ids"):
                all_account_ids += account_ids.mapped("id")
            rec.account_ids = [Command.set(list(set(all_account_ids)))]

    def get_f4_report_data(self):
        self.ensure_one()
        root_account_ids = self.env["budget.account"].search(
            [
                ("parent_id", "=", False),
                ("id", "in", self.account_ids.mapped(lambda x: x.id)),
            ],
            order="code",
        )

        def _process_account(account_id, array, deduct):
            rows = self.deduct_line_ids if deduct else self.line_ids
            rows = rows.filtered(
                lambda x: x.account_id.parent_path.startswith(account_id.parent_path)
                or ("/" + account_id.parent_path) in x.account_id.parent_path
            )

            balance = sum(rows.mapped("balance"))

            if rows:
                array.append(
                    {
                        "id": account_id.id,
                        "code": account_id.code,
                        "name": account_id.name,
                        "hierarchy_level": account_id.hierarchy_level,
                        "balance": balance,
                        "sub_rows": [
                            {
                                "id": line.id,
                                "description": line.description,
                                "note": line.note,
                            }
                            for line in rows.filtered(
                                lambda x: x.account_id.id == account_id.id
                            )
                        ],
                    }
                )

            for child_id in account_id.child_ids:
                _process_account(child_id, array, deduct)

        line_ids = []
        for account_id in root_account_ids.filtered(lambda x: not x.deduct):
            _process_account(account_id, line_ids, False)

        deduct_ids = []
        for account_id in root_account_ids.filtered(lambda x: x.deduct):
            _process_account(account_id, deduct_ids, True)

        return {
            "id": self.id,
            "name": self.name,
            "account_fiscal_year": self.account_fiscal_year_id.name,
            "source_analytic_name": self.source_analytic_id.complete_name,
            "line_ids": line_ids,
            "deduct_ids": deduct_ids,
        }


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    account_ids = fields.Many2many(
        "budget.account",
        compute="_compute_account_ids",
        context={"active_test": False},
        string="Budget Accounts",
        help="Budget accounts computed from budget account hierarchy.",
    )

    @api.depends("account_id")
    def _compute_account_ids(self):
        for rec in self:
            account_ids = [
                int(account_id)
                for account_id in rec.account_id.parent_path.strip("/").split("/")
            ]
            rec.account_ids = [Command.set(account_ids)]

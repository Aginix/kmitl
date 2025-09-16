# -*- coding: utf-8 -*-
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    """
    Budget Transfer - Extended with Procurement Plan Analytics
    
    This model extends the base budget.transfer to add support for 
    procurement plan analytic tracking. This allows budget transfers
    to be associated with specific procurement plans for better
    traceability and reporting.
    
    Business Purpose:
        Extends budget transfers to support procurement plan analytics,
        enabling better tracking of budget movements related to specific
        procurement activities and maintaining consistency with the
        procurement_plan_budget module.
    
    Key Features:
        • Add procurement_plan_analytic_id field
        • Include procurement plan in budget validation logic
        • Pass procurement plan data to generated budget moves
        • Maintain audit trail for procurement-related transfers
    """
    
    _inherit = "budget.transfer"
    
    # Procurement Plan Analytics Field
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        readonly=False,
        states={
            "submitted": [("readonly", True)],
            "approved": [("readonly", True)],
            "posted": [("readonly", True)],
            "rejected": [("readonly", True)],
            "cancelled": [("readonly", True)],
        },
        tracking=True,
        help="Procurement plan for this transfer - links budget movement to specific procurement activities",
    )
    
    @api.depends("line_ids", "amount", "state", "procurement_plan_analytic_id") 
    def _compute_budget_validation(self):
        """
        Extend budget validation to include procurement plan analytics.
        
        This method extends the parent validation to consider procurement plan
        analytics when checking budget availability. The procurement plan data
        is passed to the budget controller for comprehensive validation.
        
        Extended Validation Process:
        1. Call parent validation logic for basic checks
        2. For each FROM line, include procurement_plan_analytic_id in validation
        3. Pass extended analytic data to budget controller
        4. Generate enhanced validation messages
        """
        for transfer in self:
            if not transfer.line_ids or transfer.state in ("posted", "cancelled"):
                transfer.has_sufficient_budget = True
                transfer.budget_validation_message = ""
                continue

            try:
                # Validate each line's budget availability with procurement plan
                validation_results = []

                for line in transfer.line_ids.filtered(
                    lambda l: l.transfer_direction == "from"
                ):
                    # Check budget availability using budget controller
                    budget_controller = self.env["budget.controller"]

                    # Build analytic data for budget controller
                    # Extended to include procurement plan analytics
                    analytic_data = {}
                    if line.activity_analytic_id:
                        analytic_data["activity_analytic_id"] = line.activity_analytic_id.id
                    if line.department_analytic_id:
                        analytic_data["department_analytic_id"] = line.department_analytic_id.id
                    if line.fund_analytic_id:
                        analytic_data["fund_analytic_id"] = line.fund_analytic_id.id
                    if line.source_analytic_id:
                        analytic_data["source_analytic_id"] = line.source_analytic_id.id
                    if line.budget_account_id:
                        analytic_data["account_id"] = line.budget_account_id.id
                    
                    # Include procurement plan analytics if available
                    if transfer.procurement_plan_analytic_id:
                        analytic_data["procurement_plan_analytic_id"] = transfer.procurement_plan_analytic_id.id

                    available_budget = budget_controller.get_available_budget(
                        analytic_data=analytic_data,
                        fiscal_year_id=(
                            transfer.date_range_fy_id.id
                            if transfer.date_range_fy_id
                            else False
                        ),
                        company_id=transfer.company_id.id,
                    )

                    if available_budget < line.amount:
                        shortage = line.amount - available_budget
                        validation_results.append(
                            {
                                "line": line,
                                "available": available_budget,
                                "required": line.amount,
                                "shortage": shortage,
                                "valid": False,
                            }
                        )
                    else:
                        validation_results.append(
                            {
                                "line": line,
                                "available": available_budget,
                                "required": line.amount,
                                "shortage": 0,
                                "valid": True,
                            }
                        )

                # Determine overall validation status
                all_valid = all(result["valid"] for result in validation_results)
                transfer.has_sufficient_budget = all_valid

                # Generate enhanced validation message including procurement plan info
                if not all_valid:
                    messages = []
                    for result in validation_results:
                        if not result["valid"]:
                            # Include procurement plan in error message if available
                            account_info = f"Account {result['line'].budget_account_id.code}"
                            if transfer.procurement_plan_analytic_id:
                                account_info += f" (Procurement Plan: {transfer.procurement_plan_analytic_id.name})"
                            
                            messages.append(
                                f"{account_info}: "
                                f"Available {result['available']:,.2f}, "
                                f"Required {result['required']:,.2f}, "
                                f"Shortage {result['shortage']:,.2f}"
                            )
                    transfer.budget_validation_message = (
                        "Insufficient budget:\n" + "\n".join(messages)
                    )
                else:
                    validation_msg = "Budget validation passed"
                    if transfer.procurement_plan_analytic_id:
                        validation_msg += f" (Procurement Plan: {transfer.procurement_plan_analytic_id.name})"
                    transfer.budget_validation_message = validation_msg

            except Exception as e:
                transfer.has_sufficient_budget = False
                transfer.budget_validation_message = f"Validation error: {str(e)}"

    def _create_budget_moves(self):
        """
        Extend budget move creation to include procurement plan analytics.
        
        This method extends the parent budget move creation to ensure that
        procurement plan analytics are properly included in the generated
        budget moves and move lines for complete traceability.
        
        Extended Creation Process:
        1. Call parent validation and setup logic
        2. Create budget move with procurement plan data
        3. Create move lines with procurement plan analytics
        4. Maintain data consistency across the transfer chain
        """
        self.ensure_one()

        # Validate that we have balanced lines before creating moves
        from_total = sum(
            self.line_ids.filtered(lambda l: l.transfer_direction == "from").mapped("amount")
        )
        to_total = sum(
            self.line_ids.filtered(lambda l: l.transfer_direction == "to").mapped("amount")
        )

        if abs(from_total - to_total) > 0.01:
            raise ValidationError(
                _("Transfer lines are not balanced. FROM: {:,.2f}, TO: {:,.2f}").format(
                    from_total, to_total
                )
            )

        # Create a single budget move for the transfer
        move_vals = {
            "move_type": "entry",
            "date": self.date,
            "ref": f"Transfer: {self.name}",
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "journal_id": self._get_transfer_journal().id,
            "transfer_id": self.id,
            "date_range_fy_id": self.date_range_fy_id.id,
        }

        budget_move = self.env["budget.move"].create(move_vals)

        # Collect all move line data first, then create in batch
        move_lines_data = []
        total_debits = 0.0
        total_credits = 0.0

        for line in self.line_ids:
            # In budget accounting: FROM (source) = Credit, TO (destination) = Debit
            debit_amount = line.amount if line.transfer_direction == "to" else 0.0
            credit_amount = line.amount if line.transfer_direction == "from" else 0.0
            balance_amount = (
                line.amount if line.transfer_direction == "to" else -line.amount
            )

            total_debits += debit_amount
            total_credits += credit_amount

            line_vals = {
                "move_id": budget_move.id,
                "account_id": line.budget_account_id.id,
                "analytic_distribution": line.analytic_distribution,
                "activity_analytic_id": line.activity_analytic_id.id,
                "department_analytic_id": line.department_analytic_id.id,
                "fund_analytic_id": line.fund_analytic_id.id,
                "source_analytic_id": line.source_analytic_id.id,
                "name": line.description or f"Transfer {line.transfer_direction.upper()}",
                "debit": debit_amount,
                "credit": credit_amount,
                "balance": balance_amount,
            }
            
            # Include procurement plan analytics if available
            if self.procurement_plan_analytic_id:
                line_vals["procurement_plan_analytic_id"] = self.procurement_plan_analytic_id.id

            move_lines_data.append(line_vals)

        # Validate the move is balanced before creating lines
        if abs(total_debits - total_credits) > 0.01:
            raise ValidationError(
                _(
                    "Budget move is not balanced. Total debits: {:,.2f}, Total credits: {:,.2f}"
                ).format(total_debits, total_credits)
            )

        # Create all move lines in a single batch transaction
        self.env["budget.move.line"].create(move_lines_data)

        # Post the budget move immediately
        budget_move.action_review()
        budget_move.action_post()

        return budget_move


class BudgetTransferLine(models.Model):
    """
    Budget Transfer Line - Extended with Procurement Plan Analytics
    
    This model extends budget.transfer.line to ensure consistency
    with the procurement plan analytics added to the parent transfer.
    While the procurement plan is stored at the transfer level,
    this ensures the line-level data remains consistent.
    """
    
    _inherit = "budget.transfer.line"
    
    # Related field for easy access and consistency
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        related="transfer_id.procurement_plan_analytic_id",
        string="แผนจัดซื้อจัดจ้าง",
        readonly=True,
        store=False,
        help="Procurement plan from parent transfer",
    )
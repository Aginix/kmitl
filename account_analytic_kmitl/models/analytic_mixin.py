import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AnalyticDistributionMixin(models.AbstractModel):
    _name = "analytic.distribution.mixin"
    _inherit = ["analytic.mixin"]
    _description = "Analytic Distribution Mixin"

    # Define the Many2one fields for each analytic dimension
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
    )

    @api.onchange("activity_analytic_id", "department_analytic_id", "fund_analytic_id", "source_analytic_id")
    def _onchange_analytic_dimensions(self):
        """Update analytic_distribution when individual fields change, preserving other plans."""
        # Start with existing distribution
        distribution = dict(self.analytic_distribution or {})
        
        # Get all existing accounts and their plans
        existing_accounts = {}
        if distribution:
            account_ids = []
            for aid in distribution.keys():
                try:
                    account_ids.append(int(aid))
                except (ValueError, TypeError):
                    continue
                    
            if account_ids:
                accounts = self.env["account.analytic.account"].browse(account_ids).exists()
                for acc in accounts:
                    if acc.root_plan_id:
                        existing_accounts[acc.root_plan_id.code] = str(acc.id)
        
        # Remove accounts from plans that we're managing
        managed_plans = {
            "activities": self.activity_analytic_id,
            "departments": self.department_analytic_id,
            "funds": self.fund_analytic_id,
            "sources": self.source_analytic_id
        }
        
        # Remove old accounts from managed plans
        for plan_code, old_acc_id in existing_accounts.items():
            if plan_code in managed_plans:
                distribution.pop(old_acc_id, None)
        
        # Add new accounts from managed plans with 100%
        for plan_code, account in managed_plans.items():
            if account:
                distribution[str(account.id)] = 100.0
        
        # Update the analytic_distribution field
        self.analytic_distribution = distribution if distribution else False

    @api.model
    def create(self, vals):
        """Sync analytic_distribution on create."""
        record = super().create(vals)
        record._sync_analytic_distribution()
        return record

    def write(self, vals):
        """Sync analytic_distribution on write."""
        res = super().write(vals)
        if any(f in vals for f in ["activity_analytic_id", "department_analytic_id", "fund_analytic_id", "source_analytic_id"]):
            self._sync_analytic_distribution()
        return res

    def _sync_analytic_distribution(self):
        """Sync individual fields to analytic_distribution, preserving other plans."""
        for record in self:
            # Start with existing distribution
            distribution = dict(record.analytic_distribution or {})
            
            # Get all existing accounts and their plans
            existing_accounts = {}
            if distribution:
                account_ids = []
                for aid in distribution.keys():
                    try:
                        account_ids.append(int(aid))
                    except (ValueError, TypeError):
                        continue
                        
                if account_ids:
                    accounts = self.env["account.analytic.account"].browse(account_ids).exists()
                    for acc in accounts:
                        if acc.root_plan_id:
                            existing_accounts[acc.root_plan_id.code] = str(acc.id)
            
            # Remove accounts from plans that we're managing
            managed_plans = {
                "activities": record.activity_analytic_id,
                "departments": record.department_analytic_id,
                "funds": record.fund_analytic_id,
                "sources": record.source_analytic_id
            }
            
            # Remove old accounts from managed plans
            for plan_code, old_acc_id in existing_accounts.items():
                if plan_code in managed_plans:
                    distribution.pop(old_acc_id, None)
            
            # Add new accounts from managed plans with 100%
            for plan_code, account in managed_plans.items():
                if account:
                    distribution[str(account.id)] = 100.0
            
            # Update the analytic_distribution field
            record.analytic_distribution = distribution if distribution else False
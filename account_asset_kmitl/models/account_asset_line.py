# -*- coding: utf-8 -*-
from odoo import models


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    def _setup_move_data(self, depreciation_date):
        move_data = super()._setup_move_data(depreciation_date)
        # Stamp analytic on the journal-entry header (the "main document").
        # The header field is provided by accounting_kmitl; guard in case it
        # is not installed, since this module does not depend on it.
        if "analytic_distribution" in self.env["account.move"]._fields:
            move_data["analytic_distribution"] = self.asset_id.analytic_distribution
        return move_data

    def _setup_move_line_data(self, depreciation_date, account, ml_type, move):
        move_line_data = super()._setup_move_line_data(
            depreciation_date, account, ml_type, move
        )
        # super() stamps the depreciation line only when the
        # asset_move_line_analytic company flag is set; always carry the asset
        # analytic on every move line (depreciation and expense alike).
        move_line_data["analytic_distribution"] = self.asset_id.analytic_distribution
        return move_line_data

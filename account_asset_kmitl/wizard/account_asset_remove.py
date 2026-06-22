# -*- coding: utf-8 -*-
from odoo import models


class AccountAssetRemove(models.TransientModel):
    _inherit = "account.asset.remove"

    def remove(self):
        res = super().remove()
        # Stamp analytic on the removal journal-entry header (the "main
        # document"). The header field is provided by accounting_kmitl; guard
        # in case it is not installed, since this module does not depend on it.
        if (
            isinstance(res, dict)
            and res.get("res_model") == "account.move"
            and res.get("domain")
            and "analytic_distribution" in self.env["account.move"]._fields
        ):
            for move in self.env["account.move"].search(res["domain"]):
                assets = move.line_ids.mapped("asset_id")
                if len(assets) == 1:
                    move.analytic_distribution = assets.analytic_distribution
        return res

    def _get_removal_data(self, asset, residual_value):
        move_lines = super()._get_removal_data(asset, residual_value)
        # super() stamps analytic only on the P&L lines (and honours the
        # asset_move_line_analytic flag for the rest); always carry the asset
        # analytic on every removal move line.
        for move_line in move_lines:
            move_line[2]["analytic_distribution"] = asset.analytic_distribution
        return move_lines

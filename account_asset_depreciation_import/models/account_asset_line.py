# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    @api.depends("amount", "previous_id", "type")
    def _compute_values(self):
        """Override to include import amount in the first line's depreciated_value."""
        self.depreciated_value = 0.0
        self.remaining_value = 0.0
        dlines = self
        if self.env.context.get("no_compute_asset_line_ids"):
            exclude_ids = self.env.context["no_compute_asset_line_ids"]
            dlines = self.filtered(lambda l: l.id not in exclude_ids)
        dlines = dlines.filtered(lambda l: l.type == "depreciate")
        dlines = dlines.sorted(key=lambda l: l.line_date)
        all_excluded_lines = self - dlines
        all_excluded_lines.depreciated_value = 0
        all_excluded_lines.remaining_value = 0
        asset_ids = dlines.mapped("asset_id")
        grouped_dlines = []
        for asset in asset_ids:
            grouped_dlines.append(dlines.filtered(lambda l: l.asset_id.id == asset.id))
        for dlines in grouped_dlines:
            for i, dl in enumerate(dlines):
                if i == 0:
                    depreciation_base = dl.depreciation_base
                    import_amount = dl.asset_id.already_depreciated_amount_import
                    if dl.previous_id:
                        tmp = depreciation_base - dl.previous_id.remaining_value
                        depreciated_value = tmp
                    else:
                        depreciated_value = import_amount
                    remaining_value = (
                        depreciation_base - depreciated_value - dl.amount
                    )
                else:
                    depreciated_value += dl.previous_id.amount
                    remaining_value -= dl.amount
                dl.depreciated_value = depreciated_value
                dl.remaining_value = remaining_value

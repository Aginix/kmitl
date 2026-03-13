from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAssetLine(models.Model):
    _inherit = "account.asset.line"

    profile_id = fields.Many2one(
        comodel_name="account.asset.profile",
        string="Asset Profile",
        related="asset_id.profile_id",
        store=True,
    )

    def action_batch_create_move(self):
        """Batch-post depreciation journal entries for selected lines."""
        invalid = self.filtered(
            lambda l: l.type != "depreciate"
            or l.move_check
            or l.init_entry
            or l.parent_state != "open"
        )
        if invalid:
            raise UserError(
                _(
                    "The following lines cannot be posted: %s\n"
                    "Only pending depreciation lines on open assets are allowed."
                )
                % ", ".join(invalid.mapped("name"))
            )
        created_move_ids = self.create_move()
        return {
            "name": _("Depreciation Entries"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", created_move_ids)],
        }

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    _VALID_PR_STATES = [
        "in_progress",
    ]

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        picking_type = False
        company_id = False
        for line in self.env["purchase.request.line"].browse(request_line_ids):
            if line.request_id.state == "done":
                raise UserError(_("The purchase has already been completed."))
            if line.request_id.state not in self._VALID_PR_STATES:
                raise UserError(
                    _("Purchase Request %s is not approved or in progress")
                    % line.request_id.name
                )
            if line.purchase_state == "done":
                raise UserError(_("The purchase has already been completed."))
            line_company_id = line.company_id and line.company_id.id or False
            if company_id is not False and line_company_id != company_id:
                raise UserError(
                    _("You have to select lines from the same company.")
                )
            else:
                company_id = line_company_id
            line_picking_type = line.request_id.picking_type_id or False
            if not line_picking_type:
                raise UserError(_("You have to enter a Picking Type."))
            if picking_type is not False and line_picking_type != picking_type:
                raise UserError(
                    _("You have to select lines from the same Picking Type.")
                )
            else:
                picking_type = line_picking_type

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        request = self.item_ids.request_id
        vals.update(
            {
                "operating_unit_id": request.operating_unit_id.id,
                "account_fiscal_year_id": request.account_fiscal_year_id.id,
                "requesting_operating_unit_id": request.operating_unit_id.id,
                "payment_type": request.payment_type,
                "procurement_method_id": request.procurement_method_id.id,
            }
        )
        return vals

    def make_purchase_order(self):
        for item in self.item_ids:
            if item.line_id.purchase_lines:
                raise UserError(
                    _(
                        "The purchase request '%s' already has a Purchase Order."
                    )
                    % item.line_id.display_name
                )
        return super().make_purchase_order()


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    keep_description = fields.Boolean(
        default=True,
    )
    keep_estimated_cost = fields.Boolean(
        default=True,
    )

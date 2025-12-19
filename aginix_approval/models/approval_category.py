from odoo import api, fields, models, tools, _


class ApprovalCategory(models.Model):

    _name = "approval.category"
    _description = "Approval Category"

    name = fields.Char(
        string="Name",
        required=True
    )

    image = fields.Binary(
        string="Image"
    )

    group_id = fields.Many2one(
        string="Request Group",
        comodel_name="approval.category.group",
        required=True
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    sequence = fields.Integer(
        string="Sequence"
    )

    description = fields.Text(
        string="Description"
    )

    has_period = fields.Boolean(
        string="Has Period",
        default=False,
        required=True
    )

    has_city = fields.Boolean(
        string="Has City",
        default=False,
        required=True
    )

    has_country_id = fields.Boolean(
        string="Has Country",
        default=False,
        required=True
    )

    allowed_product_ids = fields.Many2many(
        string="Allowed Expenses",
        comodel_name="product.product",
    )

    def create_request(self):
        self.ensure_one()
        # If category uses sequence, set next sequence as name
        # (if not, set category name as default name).
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "views": [[False, "form"]],
            "context": {
                'form_view_initial_mode': 'edit',
                'default_name': "/",
                'default_category_id': self.id,
            },
        }

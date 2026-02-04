import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    purchase_ok = fields.Boolean(
        default=False,
        help="If checked, this budget account can be used in procurement.",
        tracking=True,
    )
    product_id = fields.Many2one(
        "product.product", string="Product", tracking=True, copy=False
    )

    def _get_record_url(self):
        return f"/web#id={self.id}&model={self._name}&view_type=form"

    def action_create_product(self):
        for rec in self:
            rec._create_product()

    def _create_product(self):
        self.ensure_one()

        if self.budget_type != "expense":
            return

        if not self.purchase_ok:
            return

        if self.product_id:
            return

        product_id = self.env["product.product"].create(self._prepare_product_vals())

        product_id.message_post(
            body=_(
                "The product has been created from budget account: "
                '<a href="%(link)s" target="_blank">%(name)s</a>',
                link=self._get_record_url(),
                name=f"[{self.code}] {self.name}",
            ),
            message_type="comment",
        )

        self.product_id = product_id.id

    def _prepare_product_vals(self):
        property_account_expense_id = self.env["account.account"].search(
            [("code", "=", self.code)], limit=1
        )
        return {
            "name": self.name,
            "default_code": self.code,
            "list_price": 1,
            "sale_ok": False,
            "purchase_ok": True,
            "company_id": False,
            "property_account_expense_id": property_account_expense_id.id,
            "type": "consu",
            "categ_id": self._get_or_create_product_category().id,
        }

    def _get_or_create_product_category(self):
        parent_ids = [int(n) for n in self.parent_path.strip("/").split("/")]
        # Pop the self ID
        parent_ids.pop()
        budget_account_ids = self.env["budget.account"].browse(parent_ids)

        parent_id = self.env.ref("product.cat_expense", raise_if_not_found=False)
        for budget_account_id in budget_account_ids:
            categ = self.env["product.category"].search(
                [("code", "=", budget_account_id.code)], limit=1
            )

            if not categ:
                vals = budget_account_id._prepare_product_category_vals()
                vals["parent_id"] = parent_id.id
                categ = self.env["product.category"].create(vals)

            parent_id = categ

        return parent_id

    def _prepare_product_category_vals(self):
        account_expense_id = self.env["account.account"].search(
            [("code", "=", self.code)], limit=1
        )
        return {
            "name": self.name,
            "code": self.code,
            "property_account_expense_categ_id": account_expense_id.id,
        }

    def write(self, vals):
        if self and "active" in vals:
            if self.product_id:
                self.product_id.write({"active": vals["active"]})
                if not vals["active"]:
                    self.product_id.message_post(
                        body=_(
                            "The product has been archived from budget account: "
                            '<a href="%(link)s" target="_blank">%(name)s</a>',
                            link=self._get_record_url(),
                            name=f"[{self.code}] {self.name}",
                        ),
                        message_type="comment",
                    )
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.product_id:
                rec.product_id.write({"active": False})
                rec.product_id.message_post(
                    body=_(
                        "The product has been archived from budget account: "
                        '<a href="%(link)s" target="_blank">%(name)s</a>',
                        link=self._get_record_url(),
                        name=f"[{self.code}] {self.name}",
                    ),
                    message_type="comment",
                )

        return super().unlink()

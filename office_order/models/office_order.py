from odoo import fields, models


class OfficeOrder(models.Model):
    _name = "office.order"
    _description = "Office Order"

    _inherit = ["mail.thread"]

    _rec_name = "ref_no"

    ref_no = fields.Char("Ref. No.", required=True)
    title = fields.Char(required=True)
    date = fields.Date(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    attachment_ids = fields.One2many(
        string="Attachments",
        comodel_name="ir.attachment",
        compute="_compute_attachment_ids",
    )
    attachment_count = fields.Integer(compute="_compute_attachment_ids")

    def _compute_attachment_ids(self):
        IrAttachment = self.env["ir.attachment"]
        attachments = IrAttachment.search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )

        result = dict.fromkeys(self.ids, IrAttachment)
        for attachment in attachments:
            result[attachment.res_id] |= attachment

        for record in self:
            record.attachment_ids = result[record.id]
            record.attachment_count = len(record.attachment_ids)

    def action_get_attachment_tree_view(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("base.action_attachment")
        action["context"] = {
            "default_res_model": self._name,
            "default_res_id": self.ids[0],
        }
        action["domain"] = str(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )
        action["search_view_id"] = (
            self.env.ref("office_order.ir_attachment_view_search").id,
        )
        return action

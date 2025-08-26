from odoo import api, fields, models


class PurchaseRequestAttachment(models.Model):
    _name = "purchase.request.attachment"
    _description = "Purchase Request Attachment"

    request_id = fields.Many2one("purchase.request", string="Purchase Request")
    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "Quotation"),
            ("etc", "Etc"),
        ],
        default="tor",
    )
    upload_file = fields.Binary(string="Upload File", attachment=False)
    file_name = fields.Char(string="Filename")
    attachment_id = fields.Many2one("ir.attachment", string="Stored Attachment", readonly=True)
    description = fields.Char(string="Description")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if vals.get("upload_file") and vals.get("file_name"):
                attachment = self.env["ir.attachment"].create({
                    "name": vals.get("file_name"),
                    "datas": vals.get("upload_file"),
                    "res_model": "purchase.request",
                    "res_id": record.request_id.id,
                    "type": "binary",
                })
                record.attachment_id = attachment.id
        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if vals.get("upload_file") and vals.get("file_name"):
                attachment = self.env["ir.attachment"].create({
                    "name": vals.get("file_name"),
                    "datas": vals.get("upload_file"),
                    "res_model": "purchase.request",
                    "res_id": record.request_id.id,
                    "type": "binary",
                })
                record.attachment_id = attachment.id
        return res

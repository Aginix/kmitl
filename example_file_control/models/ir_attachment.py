from odoo import _, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def unlink(self):
        """
        ป้องกันการลบ attachment ที่ผูกกับ Binary field เมื่อ record ไม่อยู่ใน draft

        res_field ไม่ว่าง = attachment สร้างโดย Binary field (ไม่ใช่จาก chatter)
        เมื่อผู้ใช้ลบจาก chatter ก็จะผ่าน unlink() นี้เช่นกัน ทำให้ป้องกันได้ทั้ง 2 ทาง
        """
        for att in self:
            if att.res_field and att.res_model and att.res_id:
                record = self.env[att.res_model].browse(att.res_id)
                if record.exists() and hasattr(record, "state") and record.state != "draft":
                    raise UserError(
                        _(
                            "ไม่สามารถลบไฟล์ '%s' ได้ เนื่องจากเอกสารไม่อยู่ในสถานะ Draft"
                        )
                        % att.name
                    )
        return super().unlink()

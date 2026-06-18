from odoo import _, api, fields, models

READONLY_STATES = {
    "submitted": [("readonly", True)],
    "done": [("readonly", True)],
    "cancel": [("readonly", True)],
}


class ExampleFileControl(models.Model):
    """
    ตัวอย่างการควบคุมไฟล์แนบ (Binary field) ตาม state

    Demonstrates three file-control requirements:
    1. Draft: แก้ไขไฟล์ใน field ได้เสรี
    2. Submitted+: ลบไฟล์ใน field และ chatter ไม่ได้
    3. Non-draft: เพิ่มไฟล์ผ่าน chatter ได้ แต่ไม่ไปโผล่ใน field
    """

    _name = "example.file.control"
    _description = "Example File Control"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        tracking=True,
        default=lambda self: _("New"),
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    description = fields.Text(
        string="Description",
        states=READONLY_STATES,
    )

    # Binary field พร้อม filename helper
    # attachment=True → เก็บข้อมูลเป็น ir.attachment (มี res_field='document')
    # states=READONLY_STATES → Python-level readonly เมื่อ state ไม่ใช่ draft
    document = fields.Binary(
        string="เอกสารแนบ",
        attachment=True,
        states=READONLY_STATES,
    )
    document_filename = fields.Char(string="Filename")

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.write({"state": "draft"})

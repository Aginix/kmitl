# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""A supporting document attached to a WA must remain readable by a plain
internal user. Odoo core rejects any ir.attachment with `res_field` set for
non-system users (odoo/addons/base/models/ir_attachment.py — the `check()`
method), so `supporting_document_ids` attachments must never carry res_field.
"""

import base64

from odoo import Command, fields
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSupportingDocs(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.config.settings"].create(
            {"group_enable_wa_on_po": True}
        ).execute()
        cls.partner = cls.env.ref("base.res_partner_12")
        cls.product = cls.env.ref("product.product_product_7")
        cls.product.purchase_method = "purchase"
        cls.po = cls.env["purchase.order"].create({
            "partner_id": cls.partner.id,
            "order_line": [
                Command.create({
                    "product_id": cls.product.id,
                    "product_uom": cls.product.uom_id.id,
                    "name": cls.product.name,
                    "price_unit": 100.0,
                    "date_planned": fields.Datetime.now(),
                    "product_qty": 5,
                })
            ],
        })
        cls.po.button_confirm()
        cls.wa = cls.env["work.acceptance"].create({
            "purchase_id": cls.po.id,
            "partner_id": cls.partner.id,
        })
        cls.plain_user = new_test_user(
            cls.env,
            login="wa_plain_user",
            groups="base.group_user",
        )

    def _attach_supporting(self):
        attachment = self.env["ir.attachment"].create({
            "name": "evidence.pdf",
            "datas": base64.b64encode(b"pdf-bytes"),
            "res_model": "work.acceptance",
            "res_id": self.wa.id,
        })
        self.wa.write({
            "supporting_document_ids": [Command.link(attachment.id)],
        })
        return attachment

    def test_supporting_doc_keeps_res_field_empty(self):
        """Attaching a file to supporting_document_ids must not set res_field
        — setting it would trigger AccessError for non-system users."""
        attachment = self._attach_supporting()
        self.assertFalse(
            attachment.res_field,
            "supporting_document_ids attachments must leave res_field empty",
        )

    def test_plain_user_can_read_wa_with_supporting_doc(self):
        """A plain internal user can read a WA whose supporting_document_ids
        contains an attachment — this is the regression from PR #1026."""
        self._attach_supporting()
        wa_as_user = self.wa.with_user(self.plain_user)
        # Reading fields on the WA and the m2m must not raise.
        wa_as_user.read(["name", "state"])
        wa_as_user.supporting_document_ids.read(["name"])

    def test_supporting_doc_excluded_from_attachment_ids(self):
        """attachment_ids (the "Attachment" tab) must not overlap with
        supporting_document_ids — they are displayed in separate places."""
        attachment = self._attach_supporting()
        self.wa.invalidate_recordset(["attachment_ids"])
        self.assertIn(attachment, self.wa.supporting_document_ids)
        self.assertNotIn(attachment, self.wa.attachment_ids)

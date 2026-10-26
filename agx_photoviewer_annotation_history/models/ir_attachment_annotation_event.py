from odoo import fields, models


class IrAttachmentAnnotationEvent(models.Model):
    """One addition, change or removal on the Annotation layer of an
    attachment. Kept once the annotation is removed, so the History still
    shows it (ADR-0001). Like annotations, only system users have an ACL:
    users read events through ``annotation_history``.
    """

    _name = "ir.attachment.annotation.event"
    _description = "Attachment Annotation Event"
    _order = "date, id"

    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    annotation_id = fields.Integer(
        required=True, help="ID of the annotation, kept once it is removed."
    )
    session_key = fields.Char(
        index=True,
        help="Visit of the photo viewer the event was made in; the events of "
        "one visit form one Change.",
    )
    operation = fields.Selection(
        selection=[("add", "Added"), ("change", "Changed"), ("remove", "Removed")],
        required=True,
    )
    user_id = fields.Many2one(comodel_name="res.users", required=True)
    date = fields.Datetime(required=True, default=fields.Datetime.now)
    before = fields.Json(
        help="The annotation before the event: page, kind, geometry, color and text."
    )
    after = fields.Json(help="The annotation after the event.")

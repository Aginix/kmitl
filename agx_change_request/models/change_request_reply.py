from odoo import fields, models


class ChangeRequestReply(models.Model):
    """One message of the conversation on a Change request (see CONTEXT.md):
    never changed once posted. Read and written through change.request."""

    _name = "change.request.reply"
    _description = "Change Request Reply"
    _order = "id"

    request_id = fields.Many2one(
        comodel_name="change.request", required=True, index=True, ondelete="cascade"
    )
    author_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="restrict",
        default=lambda self: self.env.user,
    )
    body = fields.Text(required=True)

    def _format(self):
        return [
            {
                "id": reply.id,
                "author_name": reply.author_id.name,
                "date": fields.Datetime.to_string(reply.create_date),
                "body": reply.body,
                "by_request_author": reply.author_id == reply.request_id.author_id,
            }
            for reply in self
        ]

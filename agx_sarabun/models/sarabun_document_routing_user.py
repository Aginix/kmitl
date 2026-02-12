# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SarabunDocumentRoutingUser(models.Model):
    """Pre-resolved users for a routing step.

    Created when a routing is added, recording which users are
    resolved for each routing step. Used as template for creating
    recipients when the document is sent.
    """

    _name = "sarabun.document.routing.user"
    _description = "Routing User"
    _order = "sequence, id"

    routing_id = fields.Many2one(
        comodel_name="sarabun.document.routing",
        string="Routing",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    resolution_reason = fields.Selection(
        selection=[
            ("direct", "Direct User"),
            ("dept_officer", "Department Officer"),
            ("dept_manager", "Department Manager"),
            ("role_static", "Static Role Assignment"),
            ("role_dynamic", "Dynamic Role Resolution"),
        ],
        string="Resolution Reason",
    )

    # === Computed Fields ===
    document_id = fields.Many2one(
        related="routing_id.document_id",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "unique_routing_user",
            "UNIQUE(routing_id, user_id)",
            "Each user can only appear once per routing.",
        ),
    ]

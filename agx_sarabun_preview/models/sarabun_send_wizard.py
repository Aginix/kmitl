# -*- coding: utf-8 -*-
"""Routing-timeline preview extension for sarabun.send.wizard.

Mirrors ``routing_preview_json`` from the linked document so the
SarabunRoutingTimeline widget in the wizard reads from the same field name as
on the form — one component, two surfaces, no shape divergence.
"""
from odoo import fields, models


class SarabunSendWizard(models.TransientModel):
    _inherit = "sarabun.send.wizard"

    routing_preview_json = fields.Text(
        related="document_id.routing_preview_json",
        readonly=True,
        string="Routing Timeline Payload",
    )

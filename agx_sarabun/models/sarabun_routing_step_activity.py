# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunRoutingStepActivity(models.Model):
    """Exact step ↔ mail.activity link so first-to-act clearing is precise even
    with several concurrent active steps on one Document (parallel Stages). §1.4 / §7.2.
    """

    _name = "sarabun.routing.step.activity"
    _description = "Sarabun Step ↔ Activity link"

    step_id = fields.Many2one(
        "sarabun.routing.step", required=True, ondelete="cascade", index=True
    )
    activity_id = fields.Many2one(
        "mail.activity", required=True, ondelete="cascade", index=True
    )
    user_id = fields.Many2one("res.users", required=True, index=True)

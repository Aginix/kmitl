# -*- coding: utf-8 -*-
import logging

import ast
import json as simplejson

from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Agreement(models.Model):
    _inherit = 'agreement'

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    project_ids = fields.Selection(
        [("project_1", "Project 1"), ("project_2", "Project 2")],
        string="Project",
    )

    document_ids = fields.One2many(
        "purchase.agreement.attachment",
        "request_id",
        string="Attachment",
    )

    purchase_order_id = fields.Many2one(
        'purchase.order', 
        string="PO Ref", 
        ondelete="set null",
    )

    pr1_total = fields.Monetary(related='purchase_order_id.pr1_total', string='PR1 Total')

    invoice_plan_ids = fields.One2many(
        comodel_name="purchase.invoice.plan",
        inverse_name="purchase_id",
        string="Invoice Plan",
        related="purchase_order_id.invoice_plan_ids",
        readonly=True,
    )

    work_acceptance_committee_ids = fields.One2many(
        related='purchase_order_id.work_acceptance_committee_ids',
        readonly=True,
    )
    tor_committee_ids = fields.One2many(
        related='purchase_order_id.tor_committee_ids',
        readonly=True,
    )
    price_determine_committee_ids = fields.One2many(
        related='purchase_order_id.price_determine_committee_ids',
        readonly=True,
    )
    evaluation_committee_ids = fields.One2many(
        related='purchase_order_id.evaluation_committee_ids',
        readonly=True,
    )

    fee = fields.Char(
        related='purchase_order_id.fee',
        string='Fee Per Day',
    )

    contract_type = fields.Selection(
        related='purchase_order_id.contract_type',
        string="Contract type",
        store=True,
        readonly=False
    )

    work_start_date = fields.Date(related='purchase_order_id.work_start_date', string="Work start date",)

    work_end_date = fields.Date(related='purchase_order_id.work_end_date', string="Work end date",)

    # @api.model
    # def get_view(self, view_id=None, view_type=False, **options):
    #     res = super().get_view(view_id=view_id, view_type=view_type, **options)
    #     # Readonly fields
    #     if view_type == "form":
    #         doc = etree.XML(res["arch"])
    #         for node in doc.xpath("//field"):
    #             if (
    #                 node in doc.xpath("//tree/field")
    #                 or node.attrib.get("name") in self._exclude_readonly_field()
    #             ):
    #                 continue
    #             attrs = ast.literal_eval(node.attrib.get("attrs", "{}"))
    #             if attrs:
    #                 if attrs.get("readonly"):
    #                     attrs["readonly"] = ["|", ("readonly", "=", True)] + attrs[
    #                         "readonly"
    #                     ]
    #                 else:
    #                     attrs["readonly"] = [("readonly", "=", True)]
    #             else:
    #                 attrs["readonly"] = [("readonly", "=", True)]
    #             node.set("attrs", simplejson.dumps(attrs))
    #             modifiers = ast.literal_eval(
    #                 node.attrib.get("modifiers", "{}")
    #                 .replace("true", "True")
    #                 .replace("false", "False")
    #             )
    #             readonly = modifiers.get("readonly")
    #             invisible = modifiers.get("invisible")
    #             required = modifiers.get("required")
    #             attrs = modifiers.get("attrs")
    #             if isinstance(readonly, bool) and readonly:
    #                 attrs["readonly"] = readonly
    #             if isinstance(invisible, bool) and invisible:
    #                 attrs["invisible"] = invisible
    #             if isinstance(required, bool) and required:
    #                 attrs["required"] = required
    #             if isinstance(attrs, str) and attrs:
    #                 attrs["attrs"] = attrs
    #             node.set("modifiers", simplejson.dumps(attrs))
    #         res["arch"] = etree.tostring(doc)
    #     return res

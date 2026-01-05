# -*- coding: utf-8 -*-
import ast
import json

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type not in ('form', 'tree'):
            return result

        model_name = self._name

        configs = self.env['readonly.management'].sudo().search([
            ('model.model', '=', model_name)
        ])

        if not configs:
            return result

        managed_fields = set()
        for cfg in configs:
            managed_fields.update(cfg.field_ids.mapped('name'))
            domain = False
            if cfg.domain:
                try:
                    domain = ast.literal_eval(cfg.domain)
                except Exception:
                    domain = False

        if not managed_fields:
            return result

        doc = etree.fromstring(result['arch'])

        for field_name in managed_fields:
            nodes = doc.xpath(f"//field[@name='{field_name}']")
            for node in nodes:
                modifiers = json.loads(node.get('modifiers', '{}'))

                if domain:
                    modifiers['readonly'] = domain
                else:
                    modifiers['readonly'] = False

                if 'attrs' in modifiers:
                    attrs = modifiers.get('attrs', {})
                    attrs.pop('readonly', None)
                    modifiers['attrs'] = attrs

                node.set('modifiers', json.dumps(modifiers))

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

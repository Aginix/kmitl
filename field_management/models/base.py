# -*- coding: utf-8 -*-
import ast
import json

from lxml import etree

from odoo import _, api, fields, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if not self._is_readonly_management_applicable(view_type):
            return result

        configs = self._get_readonly_management_configs()
        if not configs:
            return result

        field_domain_map = self._prepare_field_domain_map(configs)
        if not field_domain_map:
            return result

        doc = etree.fromstring(result['arch'])
        self._apply_readonly_management_on_arch(doc, field_domain_map)

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    def _is_readonly_management_applicable(self, view_type):
        return view_type in ('form', 'tree')

    def _get_readonly_management_configs(self):
        return self.env['readonly.management'].sudo().search([
            ('model_id.model', '=', self._name)
        ])

    def _prepare_field_domain_map(self, configs):
        field_map = {}

        for cfg in configs:
            unlock_domain = self._parse_unlock_domain(cfg.domain)

            for field in cfg.field_ids:
                field_map[field.name] = unlock_domain

        return field_map

    def _parse_unlock_domain(self, domain_str):
        if not domain_str:
            return False
        try:
            return ast.literal_eval(domain_str)
        except Exception:
            return False

    def _apply_readonly_management_on_arch(self, doc, field_domain_map):
        for field_name, unlock_domain in field_domain_map.items():
            nodes = doc.xpath(f"//field[@name='{field_name}']")
            for node in nodes:
                self._apply_readonly_on_node(node, unlock_domain)

    def _apply_readonly_on_node(self, node, unlock_domain):
        modifiers = json.loads(node.get('modifiers', '{}'))

        if unlock_domain:
            modifiers['readonly'] = unlock_domain
        else:
            modifiers['readonly'] = False

        attrs = modifiers.get('attrs', {})
        attrs.pop('readonly', None)
        modifiers['attrs'] = attrs

        node.set('modifiers', json.dumps(modifiers))

# -*- coding: utf-8 -*-
import ast
import json

from lxml import etree

from odoo import _, api, fields, models
from odoo.osv.expression import AND, OR


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type not in ('form', 'tree'):
            return result

        model_name = self._name

        configs = self.env['readonly.management'].sudo().search([
            ('model_id.model', '=', model_name)
        ])

        if not configs:
            return result

        field_rules = {}

        for cfg in configs:
            apply_domain = None
            if cfg.apply_on_domain:
                try:
                    apply_domain = ast.literal_eval(cfg.apply_on_domain)
                except Exception:
                    continue  # domain พัง → ข้าม config นี้

            for field_cfg in cfg.field_ids:
                field_name = field_cfg.field_id.name
                field_domain = True
                if field_cfg.domain:
                    try:
                        field_domain = ast.literal_eval(field_cfg.domain)
                    except Exception:
                        continue

                final_domain = field_domain
                if apply_domain and field_domain is not True:
                    final_domain = AND([apply_domain, field_domain])

                field_rules.setdefault(field_name, []).append(final_domain)

        if not field_rules:
            return result

        doc = etree.fromstring(result['arch'])

        for field_name, domains in field_rules.items():
            for node in doc.xpath(f"//field[@name='{field_name}']"):
                modifiers = json.loads(node.get('modifiers', '{}'))

                readonly_domain = domains[0]

                modifiers['readonly'] = readonly_domain

                if 'attrs' in modifiers:
                    modifiers['attrs'].pop('readonly', None)

                node.set('modifiers', json.dumps(modifiers))

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

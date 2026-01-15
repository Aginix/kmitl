# -*- coding: utf-8 -*-
import ast
import json

from lxml import etree

from odoo import _, api, fields, models
from odoo.osv.expression import AND, OR


class Base(models.AbstractModel):
    _inherit = 'base'

    def _extract_domain_fields(self, domain):
        fields = set()

        def _walk(d):
            """
                ไล่ domain เพื่อหา field name
            """
            for item in d:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    fields.add(item[0])
                elif isinstance(item, (list, tuple)):
                    _walk(item)

        _walk(domain)
        return fields

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type != 'form':
            return result

        configs = self.env['readonly.management'].sudo().search([
            ('model_id.model', '=', self._name)
        ])
        # ถ้าไม่มี config → ไม่ต้องแตะ view
        if not configs:
            return result

        """ field_rules format:
        {
            'field_name': [domain1, domain2, ...]
        }
        """
        field_rules = {}

        required_fields = set()

        for cfg in configs:
            apply_domain = None
            if cfg.apply_on_domain:
                try:
                    # เป็น Char → แปลงเป็น domain จริง
                    apply_domain = ast.literal_eval(cfg.apply_on_domain)
                    # ดึง field ที่ domain นี้ใช้ เพื่อ inject invisible field
                    required_fields |= self._extract_domain_fields(apply_domain)
                except Exception:
                    continue

            for field_cfg in cfg.field_ids:
                field_name = field_cfg.field_id.name

                field_domain = True
                if field_cfg.domain:
                    try:
                        # แปลงเป็น domain
                        field_domain = ast.literal_eval(field_cfg.domain)
                        required_fields |= self._extract_domain_fields(field_domain)
                    except Exception:
                        continue

                final_domain = field_domain
                if apply_domain and field_domain is not True:
                    final_domain = AND([apply_domain, field_domain])

                field_rules.setdefault(field_name, []).append(final_domain)

        if not field_rules:
            return result

        # แปลง arch XML เป็น DOM
        doc = etree.fromstring(result['arch'])

        # inject invisible fields
        existing_fields = {
            n.attrib['name']
            for n in doc.xpath('//field[@name]')
        }

        sheet = doc.xpath('//sheet')
        target = sheet[0] if sheet else doc

        # domain ใช้งานได้ แม้ field ไม่อยู่ใน form
        for fname in required_fields:
            if fname not in existing_fields:
                etree.SubElement(
                    target,
                    'field',
                    name=fname,
                    invisible="1"
                )

        # Apply readonly modifiers
        for field_name, domains in field_rules.items():
            for node in doc.xpath(f"//field[@name='{field_name}']"):
                modifiers = json.loads(node.get('modifiers', '{}'))
                modifiers['readonly'] = domains[0]
                modifiers.get('attrs', {}).pop('readonly', None)
                node.set('modifiers', json.dumps(modifiers))

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

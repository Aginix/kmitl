# -*- coding: utf-8 -*-
import ast
import json
import logging

from lxml import etree

from odoo import api, models
from odoo.osv.expression import AND, OR

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    def _extract_domain_fields(self, domain):
        """Extract all field names referenced in a domain."""
        field_names = set()

        def _walk(d):
            """
                ไล่ domain เพื่อหา field name
            """
            for item in d:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    field_names.add(item[0])
                elif isinstance(item, (list, tuple)):
                    _walk(item)

        _walk(domain)
        return field_names

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
                    _logger.warning(
                        "readonly.management id=%s: invalid apply_on_domain %r",
                        cfg.id, cfg.apply_on_domain,
                    )
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
                        _logger.warning(
                            "readonly.management.fields id=%s: invalid domain %r",
                            field_cfg.id, field_cfg.domain,
                        )
                        continue

                if apply_domain is not None:
                    final_domain = (
                        apply_domain if field_domain is True
                        else AND([apply_domain, field_domain])
                    )
                else:
                    final_domain = field_domain

                field_rules.setdefault(field_name, []).append(final_domain)

        if not field_rules:
            return result

        # แปลง arch XML เป็น DOM
        doc = etree.fromstring(result['arch'])

        # Inject invisible fields needed by domains but absent from the view
        existing_fields = {n.attrib['name'] for n in doc.xpath('//field[@name]')}
        sheet = doc.xpath('//sheet')
        target = sheet[0] if sheet else doc

        for fname in required_fields:
            if fname not in existing_fields:
                etree.SubElement(target, 'field', name=fname, invisible="1")

        # Apply readonly modifiers; OR multiple rules for the same field
        for field_name, domains in field_rules.items():
            if any(d is True for d in domains):
                readonly_value = True
            elif len(domains) == 1:
                readonly_value = domains[0]
            else:
                readonly_value = OR(domains)

            for node in doc.xpath(f"//field[@name='{field_name}']"):
                modifiers = json.loads(node.get('modifiers', '{}'))
                modifiers['readonly'] = readonly_value
                node.set('modifiers', json.dumps(modifiers))

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

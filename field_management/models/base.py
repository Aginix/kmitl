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

    def _build_modifier_rules(self, configs, modifier_model_label, force_field=None):
        """Build rules dict from a set of management configs.

        Returns (rules, required_fields) where rules is:
            {'field_name': [domain1, domain2, ...]}
        and required_fields is the set of field names referenced in all domains.

        force_field: name of the boolean field on field_cfg that means
        "always apply unconditionally" (e.g. 'force_readonly').
        """
        rules = {}
        required_fields = set()

        for cfg in configs:
            apply_domain = None
            if cfg.apply_on_domain:
                try:
                    apply_domain = ast.literal_eval(cfg.apply_on_domain)
                    required_fields |= self._extract_domain_fields(apply_domain)
                except Exception:
                    _logger.warning(
                        "%s id=%s: invalid apply_on_domain %r",
                        modifier_model_label, cfg.id, cfg.apply_on_domain,
                    )
                    continue

            for field_cfg in cfg.field_ids:
                field_name = field_cfg.field_id.name

                # Force flag → unconditional modifier, skip domain parsing
                if force_field and getattr(field_cfg, force_field, False):
                    final_domain = apply_domain if apply_domain is not None else True
                    rules.setdefault(field_name, []).append(final_domain)
                    continue

                field_domain = True
                if field_cfg.domain:
                    try:
                        field_domain = ast.literal_eval(field_cfg.domain)
                        required_fields |= self._extract_domain_fields(field_domain)
                    except Exception:
                        _logger.warning(
                            "%s.fields id=%s: invalid domain %r",
                            modifier_model_label, field_cfg.id, field_cfg.domain,
                        )
                        continue

                if apply_domain is not None:
                    final_domain = (
                        apply_domain if field_domain is True
                        else AND([apply_domain, field_domain])
                    )
                else:
                    final_domain = field_domain

                rules.setdefault(field_name, []).append(final_domain)

        return rules, required_fields

    def _apply_modifier_rules(self, doc, rules, modifier_key):
        """Apply modifier_key modifiers to field nodes in doc based on rules."""
        for field_name, domains in rules.items():
            if any(d is True for d in domains):
                value = True
            elif len(domains) == 1:
                value = domains[0]
            else:
                value = OR(domains)

            for node in doc.xpath(f"//field[@name='{field_name}']"):
                modifiers = json.loads(node.get('modifiers', '{}'))
                modifiers[modifier_key] = value
                node.set('modifiers', json.dumps(modifiers))

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type != 'form':
            return result

        model_domain = [('model_id.model', '=', self._name)]

        readonly_configs = self.env['readonly.management'].sudo().search(model_domain)
        invisible_configs = self.env['invisible.management'].sudo().search(model_domain)
        required_configs = self.env['required.management'].sudo().search(model_domain)

        if not readonly_configs and not invisible_configs and not required_configs:
            return result

        readonly_rules, req_fields_ro = self._build_modifier_rules(
            readonly_configs, 'readonly.management', 'force_readonly'
        )
        invisible_rules, req_fields_inv = self._build_modifier_rules(
            invisible_configs, 'invisible.management', 'force_invisible'
        )
        required_rules, req_fields_req = self._build_modifier_rules(
            required_configs, 'required.management', 'force_required'
        )

        if not readonly_rules and not invisible_rules and not required_rules:
            return result

        # แปลง arch XML เป็น DOM
        doc = etree.fromstring(result['arch'])

        # Inject invisible fields needed by domains but absent from the view
        all_required_fields = req_fields_ro | req_fields_inv | req_fields_req
        existing_fields = {n.attrib['name'] for n in doc.xpath('//field[@name]')}
        sheet = doc.xpath('//sheet')
        target = sheet[0] if sheet else doc

        for fname in all_required_fields:
            if fname not in existing_fields:
                etree.SubElement(target, 'field', name=fname, invisible="1")

        self._apply_modifier_rules(doc, readonly_rules, 'readonly')
        self._apply_modifier_rules(doc, invisible_rules, 'invisible')
        self._apply_modifier_rules(doc, required_rules, 'required')

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

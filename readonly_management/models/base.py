# -*- coding: utf-8 -*-
import ast
import json
import logging

from lxml import etree

from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# Models to skip to avoid self-referential loops
_SKIP_MODELS = frozenset(
    ["readonly.management", "readonly.management.fields"]
)


def _parse_domain(domain_str):
    """
    Parse an Odoo domain string into a Python list.
    Returns None if empty. Raises ValueError on invalid input.
    """
    if not domain_str or not domain_str.strip():
        return None
    try:
        domain = ast.literal_eval(domain_str.strip())
        if not isinstance(domain, list):
            raise ValueError("Domain must be a list, got %s" % type(domain))
        return domain
    except Exception as exc:
        raise ValueError(
            "Invalid domain %r: %s" % (domain_str, exc)
        ) from exc


def _build_condition(apply_domain, force_readonly, field_domain):
    """
    Build readonly condition from config data.

    Returns:
      True  → always readonly (inject readonly="1")
      list  → domain-based readonly (inject into attrs)
      None  → no rule to inject

    Truth table:
      apply | force | field  → result
      None  | True  | -      → True (always)
      set   | True  | -      → apply_domain
      None  | False | set    → field_domain
      set   | False | set    → AND([apply, field])
      set   | False | None   → apply_domain
      None  | False | None   → None (skip)
    """
    if force_readonly:
        return apply_domain if apply_domain else True
    if apply_domain and field_domain:
        return expression.AND([apply_domain, field_domain])
    if apply_domain:
        return apply_domain
    if field_domain:
        return field_domain
    return None


def _merge_conditions_or(conditions):
    """
    Merge a list of conditions with OR logic.
    If any condition is True (always), return True.
    Single condition: return as-is.
    Multiple: expression.OR([...]).
    """
    if True in conditions:
        return True
    if len(conditions) == 1:
        return conditions[0]
    return expression.OR(conditions)


def _domain_to_json(domain):
    """Convert Odoo domain (may contain tuples) to JSON-serializable lists."""
    if isinstance(domain, tuple):
        return list(domain)
    if isinstance(domain, list):
        return [_domain_to_json(item) for item in domain]
    return domain


def _inject_readonly(field_el, condition):
    """
    Inject or merge readonly condition onto a <field> XML element.

    In Odoo 16, postprocess_and_fields() converts attrs/readonly into a
    'modifiers' JSON attribute before get_view() returns. We must read/write
    that attribute directly — injecting attrs or readonly has no effect.

    condition is True  → modifiers readonly=true
    condition is list  → merge domain into modifiers readonly
    """
    existing_modifiers_str = field_el.get("modifiers", "")
    try:
        existing_modifiers = (
            json.loads(existing_modifiers_str) if existing_modifiers_str else {}
        )
    except Exception:
        _logger.warning(
            "readonly_management: cannot parse existing modifiers %r on <%s name=%r>, skipping",
            existing_modifiers_str,
            field_el.tag,
            field_el.get("name"),
        )
        return

    if condition is True:
        existing_modifiers["readonly"] = True
        field_el.set("modifiers", json.dumps(existing_modifiers))
        return

    # condition is a domain list
    existing_ro = existing_modifiers.get("readonly")
    if existing_ro is True or existing_ro == 1:
        return

    if existing_ro:
        # existing_ro from JSON is list-of-lists; expression handles both
        merged = _merge_conditions_or([existing_ro, condition])
    else:
        merged = condition

    if merged is True:
        existing_modifiers["readonly"] = True
    else:
        existing_modifiers["readonly"] = _domain_to_json(merged)

    field_el.set("modifiers", json.dumps(existing_modifiers))


def _is_inside_tree(element):
    """Return True if element is a descendant of a <tree> element."""
    parent = element.getparent()
    while parent is not None:
        if parent.tag == "tree":
            return True
        parent = parent.getparent()
    return False


class Base(models.AbstractModel):
    """
    Extends the base abstract model to inject readonly attrs from
    readonly.management configurations into form views at render time.
    """

    _inherit = "base"

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type != "form":
            return result

        if self._name in _SKIP_MODELS:
            return result

        configs = (
            self.env["readonly.management"]
            .sudo()
            .search([("model_name", "=", self._name), ("active", "=", True)])
        )
        if not configs:
            return result

        # Build field_name → merged condition
        field_conditions = {}

        for config in configs:
            try:
                apply_domain = _parse_domain(config.apply_on_domain)
            except ValueError:
                _logger.warning(
                    "readonly.management id=%s: invalid apply_on_domain %r, skipping config",
                    config.id,
                    config.apply_on_domain,
                )
                continue

            for rule in config.field_ids:
                fname = rule.field_name
                if not fname:
                    continue

                try:
                    field_domain = _parse_domain(rule.domain) if not rule.force_readonly else None
                except ValueError:
                    _logger.warning(
                        "readonly.management.fields id=%s: invalid domain %r, skipping rule",
                        rule.id,
                        rule.domain,
                    )
                    continue

                condition = _build_condition(apply_domain, rule.force_readonly, field_domain)
                if condition is None:
                    continue

                if fname in field_conditions:
                    field_conditions[fname].append(condition)
                else:
                    field_conditions[fname] = [condition]

        if not field_conditions:
            return result

        # Parse view arch
        arch = result.get("arch")
        if not arch:
            return result
        try:
            root = etree.fromstring(
                arch.encode("utf-8") if isinstance(arch, str) else arch
            )
        except etree.XMLSyntaxError:
            _logger.error(
                "readonly_management: cannot parse arch for model %s", self._name
            )
            return result

        modified = False
        for fname, conditions in field_conditions.items():
            merged = _merge_conditions_or(conditions)
            for field_el in root.xpath('.//field[@name="%s"]' % fname):
                if _is_inside_tree(field_el):
                    continue
                _inject_readonly(field_el, merged)
                modified = True

        if modified:
            result["arch"] = etree.tostring(root, encoding="unicode")

        return result

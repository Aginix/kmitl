import re

from lxml import etree
from lxml.builder import E

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

# Writes touching these fields change what users see and are logged.
LOGGED_FIELDS = {"arch", "arch_base", "arch_db", "active", "inherit_id", "mode", "priority"}
INSPECTABLE_TAGS = ("button", "field")
# Extension views with this priority are applied after their siblings.
HIDE_PRIORITY = 9999
SCOPE_TAGS = ("header", "footer", "sheet")
SUBVIEW_TAGS = ("tree", "form", "kanban")


def _xpath_literal(value):
    return "'%s'" % value if "'" not in value else '"%s"' % value


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    # -------------------------------------------------------------------------
    # Inspector: trace which views declare / modify an element
    # -------------------------------------------------------------------------

    @api.model
    def apply_inheritance_specs(self, source, specs_tree, pre_locate=lambda s: True):
        trace = self.env.context.get("view_origin_trace")
        if trace is None:
            return super().apply_inheritance_specs(
                source, specs_tree, pre_locate=pre_locate
            )
        before = {}
        for node in self._view_origin_match(source, trace):
            self._view_origin_track(trace, node)
            before[node] = (node.getparent(), dict(node.attrib))
        source = super().apply_inheritance_specs(
            source, specs_tree, pre_locate=pre_locate
        )
        after = self._view_origin_match(source, trace)
        for node in after:
            if node not in before:
                trace["nodes"].setdefault(node, []).append(
                    self._view_origin_event("added")
                )
                continue
            parent, attrs = before[node]
            changes = [
                {"attr": key, "old": attrs.get(key), "new": node.get(key)}
                for key in sorted(set(attrs) | set(node.attrib))
                if attrs.get(key) != node.get(key)
            ]
            if changes:
                trace["nodes"][node].append(
                    self._view_origin_event("attributes", changes)
                )
            if node.getparent() is not parent:
                trace["nodes"][node].append(self._view_origin_event("moved"))
        for node in set(before) - set(after):
            trace["nodes"][node].append(self._view_origin_event("removed"))
        return source

    @api.model
    def _view_origin_match(self, arch, trace):
        return [n for n in arch.iter(trace["tag"]) if n.get("name") == trace["name"]]

    @api.model
    def _view_origin_track(self, trace, node):
        """Nodes seen before any inheriting view touched them come from the root."""
        if node not in trace["nodes"]:
            trace["nodes"][node] = [
                {"view_id": trace["root"], "kind": "declared", "changes": []}
            ]

    def _view_origin_event(self, kind, changes=None):
        return {"view_id": self.id, "kind": kind, "changes": changes or []}

    @api.model
    def _view_origin_xpath(self, arch, node):
        """Shortest readable xpath that matches only ``node`` in ``arch``:
        prefixed by its nearest named / structural ancestors as needed."""
        xpath = "//%s[@name=%s]" % (node.tag, _xpath_literal(node.get("name")))
        if len(arch.xpath(xpath)) == 1:
            return xpath
        child = node
        for anc in node.iterancestors():
            if anc.get("name"):
                step = "%s[@name=%s]" % (anc.tag, _xpath_literal(anc.get("name")))
            elif anc.tag in SCOPE_TAGS + SUBVIEW_TAGS:
                step = anc.tag
            else:
                continue
            sep = "/" if child.getparent() is anc else "//"
            xpath = "//%s%s%s" % (step, sep, xpath[2:])
            child = anc
            # tree / form alone are not distinctive: every sub-view has one
            if anc.tag not in SUBVIEW_TAGS and len(arch.xpath(xpath)) == 1:
                return xpath
        return arch.getroottree().getpath(node)

    @api.model
    def _view_origin_area(self, node):
        """Area of ``node`` (header, button box or x2many sub-view type),
        matched against the one clicked in the UI."""
        for anc in node.iterancestors():
            parent = anc.getparent()
            if anc.tag in SUBVIEW_TAGS and parent is not None and parent.tag == "field":
                return anc.tag
            if anc.tag == "header":
                return "header"
            if anc.get("name") == "button_box" or "oe_button_box" in (
                anc.get("class") or ""
            ):
                return "button_box"
        return False

    @api.model
    def _view_origin_hide_spec(self, xpath):
        return E.xpath(
            E.attribute("1", name="invisible"), expr=xpath, position="attributes"
        )

    @api.model
    def _view_origin_record_xml(self, record_id, name, model, inherit_ref, arch):
        """``<record>`` ready to paste in a module data file."""
        record = E.record(
            E.field(name, name="name"),
            E.field(model, name="model"),
            E.field(name="inherit_id", ref=inherit_ref),
            E.field(str(HIDE_PRIORITY), name="priority"),
            E.field(*arch, name="arch", type="xml"),
            id=re.sub(r"\W+", "_", record_id).strip("_"),
            model="ir.ui.view",
        )
        etree.indent(record, space="    ")
        return etree.tostring(record, encoding="unicode")

    @api.model
    def view_origin_inspect(
        self, view_id, tag, name, parent_field=False, area=False
    ):
        """Return every occurrence of ``<tag name="name">`` in the combined
        arch of ``view_id`` with the views that declared and modified it."""
        self.check_access_rights("read")
        view = self.browse(view_id).exists()
        if not view or tag not in INSPECTABLE_TAGS or not name:
            raise UserError(_("Nothing to inspect."))
        root = view
        while root.inherit_id:
            root = root.inherit_id
        trace = {"tag": tag, "name": name, "root": root.id, "nodes": {}}
        arch = view.with_context(view_origin_trace=trace)._get_combined_arch()
        final = self._view_origin_match(arch, trace)
        for node in final:
            self._view_origin_track(trace, node)

        view_ids = {e["view_id"] for events in trace["nodes"].values() for e in events}
        views = {
            v.id: {
                "id": v.id,
                "name": v.name,
                "xml_id": v.xml_id or "",
                "module": (v.xml_id or "").split(".")[0],
                "priority": v.priority,
                "mode": v.mode,
                "arch_fs": v.arch_fs or "",
            }
            for v in self.browse(view_ids)
        }
        inherit_ref = view.xml_id or str(view.id)
        occurrences = []
        for node, events in trace["nodes"].items():
            present = node in final
            node_parent_field = next(
                (a.get("name") for a in node.iterancestors("field")), False
            )
            xpath = self._view_origin_xpath(arch, node) if present else ""
            occurrences.append(
                {
                    "xpath": xpath,
                    "present": present,
                    "parent_field": node_parent_field,
                    "matched": present
                    and node_parent_field == (parent_field or False)
                    and self._view_origin_area(node) == (area or False),
                    "attrs": dict(node.attrib),
                    "events": [dict(e, view=views[e["view_id"]]) for e in events],
                    "depends": sorted(
                        {views[e["view_id"]]["module"] for e in events} - {""}
                    ),
                    "snippet": present
                    and self._view_origin_record_xml(
                        "%s_hide_%s_%s" % (inherit_ref.split(".")[-1], tag, name),
                        "%s.hide.%s.%s" % (view.model, tag, name),
                        view.model,
                        inherit_ref,
                        [self._view_origin_hide_spec(xpath)],
                    ),
                }
            )
        occurrences.sort(key=lambda o: (not o["matched"], not o["present"]))
        return {
            "view": {"id": view.id, "name": view.name, "xml_id": view.xml_id or ""},
            "model": view.model,
            "tag": tag,
            "name": name,
            "occurrences": occurrences,
        }

    @api.model
    def view_origin_hide(self, view_id, tag, name, xpath):
        """Hide the element with an extension view applied last; logged."""
        self.check_access_rights("create")
        view = self.browse(view_id).exists()
        if not view or tag not in INSPECTABLE_TAGS:
            raise UserError(_("Nothing to hide."))
        hide_view = self.with_context(view_change_log_skip=True).create(
            {
                "name": "%s.hide.%s.%s" % (view.model, tag, name),
                "model": view.model,
                "inherit_id": view.id,
                "mode": "extension",
                "priority": HIDE_PRIORITY,
                "arch": etree.tostring(
                    E.data(self._view_origin_hide_spec(xpath)), encoding="unicode"
                ),
            }
        )
        self.env["ir.ui.view.change.log"]._log_views(
            hide_view,
            "hide",
            extra={"element": "%s %s" % (tag, name), "target_xpath": xpath},
        )
        return hide_view.id

    # -------------------------------------------------------------------------
    # Change log: manual view changes made outside module install / upgrade
    # -------------------------------------------------------------------------

    def _view_change_log_enabled(self):
        ctx = self.env.context
        return not (
            self.pool._init
            or ctx.get("install_mode")
            or ctx.get("install_filename")
            or ctx.get(MODULE_UNINSTALL_FLAG)
            or ctx.get("view_change_log_skip")
        )

    def _view_change_log_snapshot(self):
        """Text compared before/after a change: the arch preceded by the
        fields deciding whether and where it applies."""
        self.ensure_one()
        header = "<!-- active=%s mode=%s priority=%s inherit_id=%s -->" % (
            self.active,
            self.mode,
            self.priority,
            self.inherit_id.xml_id or self.inherit_id.id or "",
        )
        return "%s\n%s" % (header, self.arch or "")

    @api.model_create_multi
    def create(self, vals_list):
        views = super().create(vals_list)
        if self._view_change_log_enabled():
            self.env["ir.ui.view.change.log"]._log_views(views, "create")
        return views

    def write(self, vals):
        if not LOGGED_FIELDS & set(vals) or not self._view_change_log_enabled():
            return super().write(vals)
        before = {view.id: view._view_change_log_snapshot() for view in self}
        res = super().write(vals)
        self.env["ir.ui.view.change.log"]._log_views(self, "write", before)
        return res

    def unlink(self):
        if self._view_change_log_enabled():
            before = {view.id: view._view_change_log_snapshot() for view in self}
            self.env["ir.ui.view.change.log"]._log_views(self, "unlink", before)
        return super().unlink()

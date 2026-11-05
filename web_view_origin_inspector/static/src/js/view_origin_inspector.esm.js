/** @odoo-module **/

import {Component} from "@odoo/owl";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Dialog} from "@web/core/dialog/dialog";
import {browser} from "@web/core/browser/browser";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const BUTTON_SELECTOR = "button[name], a[type][name]";
const FIELD_SELECTOR = ".o_field_widget[name], td.o_data_cell[name], th[data-name]";
const X2MANY_SELECTOR = ".o_field_one2many[name], .o_field_many2many[name]";
const HOVER_CLASS = "o_view_origin_hover";
const INSPECTING_CLASS = "o_view_origin_inspecting";

/**
 * Map a DOM node to the arch element it was rendered from.
 * Buttons win over fields: stat buttons wrap fields, list rows wrap buttons.
 */
function resolveTarget(target) {
    let el = target.closest(BUTTON_SELECTOR);
    let tag = "button";
    let name = el && el.getAttribute("name");
    if (!el) {
        el = target.closest(FIELD_SELECTOR);
        tag = "field";
        name = el && (el.getAttribute("name") || el.dataset.name);
    }
    if (!el) {
        // Field label: its "?" carries the field tooltip in debug mode
        const label = target.closest(".o_form_label, .o_td_label");
        const info = label && label.querySelector("[data-tooltip-info]");
        try {
            name = info && JSON.parse(info.dataset.tooltipInfo).field.name;
        } catch {
            name = false;
        }
        el = name && label;
    }
    if (!el || !name) {
        return null;
    }
    const x2many = el.parentElement && el.parentElement.closest(X2MANY_SELECTOR);
    let area = false;
    if (x2many) {
        area = el.closest(".o_list_renderer") ? "tree" : false;
        area = area || (el.closest(".o_kanban_renderer") ? "kanban" : false);
    } else if (el.closest(".o_form_statusbar")) {
        area = "header";
    } else if (el.closest(".oe_button_box")) {
        area = "button_box";
    }
    return {
        el,
        tag,
        name,
        parentField: x2many ? x2many.getAttribute("name") : false,
        area,
    };
}

export class ViewOriginDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        const {tag, name} = this.props.result;
        this.title = this.env._t("View Origin: ") + `${tag} "${name}"`;
        this.kinds = {
            declared: [this.env._t("Declared"), "bg-primary"],
            added: [this.env._t("Added"), "bg-success"],
            attributes: [this.env._t("Attributes changed"), "bg-warning text-dark"],
            moved: [this.env._t("Moved"), "bg-info text-dark"],
            removed: [this.env._t("Removed"), "bg-danger"],
        };
    }

    formatAttrs(attrs) {
        return Object.entries(attrs)
            .map(([key, value]) => `${key}="${value}"`)
            .join(" ");
    }

    openView(viewId) {
        browser.open(`/web#model=ir.ui.view&id=${viewId}&view_type=form`, "_blank");
    }

    async copy(text) {
        await browser.navigator.clipboard.writeText(text);
        this.notification.add(this.env._t("Copied to clipboard"), {type: "success"});
    }

    hide(occurrence) {
        const {result} = this.props;
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t(
                "Create an extension view hiding this element now? " +
                    "It is recorded in View Change Log so it can be ported to code."
            ),
            confirm: async () => {
                await this.orm.call("ir.ui.view", "view_origin_hide", [
                    result.view.id,
                    result.tag,
                    result.name,
                    occurrence.xpath,
                ]);
                browser.location.reload();
            },
        });
    }
}
ViewOriginDialog.template = "web_view_origin_inspector.ViewOriginDialog";
ViewOriginDialog.components = {Dialog};
ViewOriginDialog.props = {
    result: Object,
    close: Function,
};

function startInspector(env, viewId) {
    const scope = document.querySelector(".o_action_manager") || document.body;
    let hovered = null;
    const setHover = (el) => {
        if (hovered) {
            hovered.classList.remove(HOVER_CLASS);
        }
        hovered = el || null;
        if (hovered) {
            hovered.classList.add(HOVER_CLASS);
        }
    };
    const block = (ev) => {
        ev.preventDefault();
        ev.stopImmediatePropagation();
    };
    const closeNotification = env.services.notification.add(
        env._t("Click a button or a field to see where it comes from. Esc to cancel."),
        {type: "info", sticky: true}
    );
    const listeners = {
        mouseover: (ev) => {
            const found = scope.contains(ev.target) && resolveTarget(ev.target);
            setHover(found && found.el);
        },
        pointerdown: (ev) => scope.contains(ev.target) && block(ev),
        mousedown: (ev) => scope.contains(ev.target) && block(ev),
        mouseup: (ev) => scope.contains(ev.target) && block(ev),
        click: async (ev) => {
            if (!scope.contains(ev.target)) {
                return;
            }
            block(ev);
            const found = resolveTarget(ev.target);
            if (!found) {
                return;
            }
            stop();
            const result = await env.services.orm.call(
                "ir.ui.view",
                "view_origin_inspect",
                [viewId, found.tag, found.name],
                {parent_field: found.parentField, area: found.area}
            );
            env.services.dialog.add(ViewOriginDialog, {result});
        },
        keydown: (ev) => {
            if (ev.key === "Escape") {
                block(ev);
                stop();
            }
        },
    };
    function stop() {
        setHover(null);
        document.body.classList.remove(INSPECTING_CLASS);
        for (const [type, handler] of Object.entries(listeners)) {
            document.removeEventListener(type, handler, true);
        }
        closeNotification();
    }
    document.body.classList.add(INSPECTING_CLASS);
    for (const [type, handler] of Object.entries(listeners)) {
        document.addEventListener(type, handler, true);
    }
}

export function inspectViewElement({accessRights, component, env}) {
    const {viewId} = component.env.config || {};
    if (!accessRights.canEditView || !viewId || "viewInfo" in component.props) {
        return null;
    }
    return {
        type: "item",
        description: env._t("Inspect View Element"),
        callback: () => startInspector(env, viewId),
        sequence: 345,
    };
}

registry.category("debug").category("view").add("inspectViewElement", inspectViewElement);

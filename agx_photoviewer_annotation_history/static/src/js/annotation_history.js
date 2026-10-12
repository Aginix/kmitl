/** @odoo-module **/

import {
    AnnotationEditor,
    htmlElement,
} from "@agx_photoviewer_annotation/js/annotation_renderer";
import {deserializeDateTime, formatDateTime} from "@web/core/l10n/dates";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {sprintf} from "@web/core/utils/strings";

const SNAPSHOT_KEYS = ["page", "kind", "color", "text"];

function isSame(a, b) {
    return (
        SNAPSHOT_KEYS.every((key) => a[key] === b[key]) &&
        JSON.stringify(a.geometry) === JSON.stringify(b.geometry)
    );
}

/**
 * Replay the `changes` returned by `annotation_history` (oldest first) and
 * return, for each one that left a mark, what it added, changed and removed
 * with the layer to draw for it (ADR-0001).
 */
function buildChanges(changes) {
    const layer = new Map();
    const result = [];
    for (const change of changes) {
        const before = new Map(layer);
        for (const event of change.events) {
            if (event.operation === "remove") {
                layer.delete(event.annotation_id);
            } else {
                layer.set(event.annotation_id, {
                    // A mark keeps the author and date it was added with.
                    author_name: change.user_name,
                    create_date: event.date,
                    ...layer.get(event.annotation_id),
                    ...event.after,
                    id: event.annotation_id,
                    is_own: false,
                });
            }
        }
        const added = new Set();
        const changed = new Set();
        const removed = new Set();
        for (const id of new Set(change.events.map((event) => event.annotation_id))) {
            const was = before.get(id);
            const now = layer.get(id);
            if (!was && now) {
                added.add(id);
            } else if (was && !now) {
                removed.add(id);
            } else if (was && now && !isSame(was, now)) {
                changed.add(id);
            }
        }
        if (!added.size && !changed.size && !removed.size) {
            continue;
        }
        const state = (id) =>
            (added.has(id) && "added") || (changed.has(id) && "changed") || "";
        result.push({
            ...change,
            added,
            changed,
            removed,
            annotations: [
                // Earlier positions and removed marks lie under the others.
                ...[...changed].map((id) => ({
                    ...before.get(id),
                    historyState: "before",
                })),
                ...[...removed].map((id) => ({
                    ...before.get(id),
                    historyState: "removed",
                })),
                ...[...layer.values()].map((annotation) => ({
                    ...annotation,
                    historyState: state(annotation.id),
                })),
            ],
        });
    }
    return result;
}

patch(AnnotationEditor.prototype, "agx_photoviewer_annotation_history", {
    buildToolbar() {
        const toolbar = this._super(...arguments);
        this.historyButton = htmlElement("button", "btn btn-sm btn-light");
        this.historyButton.type = "button";
        this.historyButton.title = _t("History");
        this.historyButton.innerHTML = '<i class="fa fa-history"></i>';
        this.historyButton.addEventListener("click", () => this.toggleHistory());
        toolbar.append(this.historyButton);
        return toolbar;
    },

    buildDom() {
        this._super(...arguments);
        this.historyPanel = htmlElement("div", "o_agx_annotation_history d-none");
        this.body.append(this.historyPanel);
    },

    visibleAnnotations() {
        return this.historyChange?.annotations || this._super(...arguments);
    },

    shape(annotation) {
        const group = this._super(...arguments);
        if (annotation.historyState) {
            group.classList.add(`o_agx_annotation_history_${annotation.historyState}`);
        }
        return group;
    },

    add() {
        return this.reloadHistoryAfter(this._super(...arguments));
    },

    update() {
        return this.reloadHistoryAfter(this._super(...arguments));
    },

    remove() {
        return this.reloadHistoryAfter(this._super(...arguments));
    },

    // ------------------------------------------------------------ history

    async reloadHistoryAfter(promise) {
        const result = await promise;
        if (!this.historyPanel.classList.contains("d-none")) {
            this.loadHistory();
        }
        return result;
    },

    toggleHistory() {
        const open = this.historyPanel.classList.contains("d-none");
        this.historyPanel.classList.toggle("d-none", !open);
        this.historyButton.classList.toggle("active", open);
        if (open) {
            this.loadHistory();
        } else {
            this.showChange(null);
        }
    },

    async loadHistory() {
        const changes = await this.call("annotation_history", this.attachment.id);
        if (this.left) {
            return;
        }
        // Newest first.
        this.historyChanges = buildChanges(changes).reverse();
        const current = this.historyChanges.find(
            (change) => change.key === this.historyChange?.key
        );
        this.renderHistory();
        this.showChange(current || null);
    },

    renderHistory() {
        const item = (change, label, meta) => {
            const element = htmlElement("button", "o_agx_annotation_history_item");
            element.type = "button";
            element.append(htmlElement("div", "o_agx_annotation_history_label", label));
            if (meta) {
                element.append(meta);
            }
            element.addEventListener("click", () => this.showChange(change));
            element.dataset.key = change?.key || "";
            return element;
        };
        const counts = (change) => {
            const element = htmlElement("div", "o_agx_annotation_history_counts");
            for (const [ids, label, className] of [
                [change.added, _t("Added %s"), "text-success"],
                [change.changed, _t("Changed %s"), "text-warning"],
                [change.removed, _t("Removed %s"), "text-danger"],
            ]) {
                if (ids.size) {
                    element.append(
                        htmlElement("span", className, sprintf(label, ids.size))
                    );
                }
            }
            return element;
        };
        const items = this.historyChanges.map((change) =>
            item(
                change,
                `${change.user_name} · ${formatDateTime(
                    deserializeDateTime(change.date)
                )}`,
                counts(change)
            )
        );
        this.historyPanel.replaceChildren(
            htmlElement("div", "o_agx_annotation_history_title", _t("History")),
            item(null, _t("Current")),
            ...items
        );
        if (!items.length) {
            this.historyPanel.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_history_empty",
                    _t("No changes recorded yet.")
                )
            );
        }
    },

    /**
     * Draw the layer as `change` left it, its marks highlighted, read-only;
     * `null` goes back to the live layer.
     */
    showChange(change) {
        this.historyChange = change;
        this.closePopover();
        if (change) {
            this.setDrawing(false);
        }
        this.drawButton.disabled = Boolean(change);
        this.root.classList.toggle("o_agx_annotation_history_mode", Boolean(change));
        for (const element of this.historyPanel.querySelectorAll(
            ".o_agx_annotation_history_item"
        )) {
            element.classList.toggle(
                "active",
                element.dataset.key === (change?.key || "")
            );
        }
        this.redraw();
        if (change) {
            this.scrollToChange(change);
        }
    },

    scrollToChange(change) {
        const pages = change.annotations
            .filter((annotation) => annotation.historyState)
            .map((annotation) => annotation.page);
        const sheet = this.sheets.find((s) => s.number === Math.min(...pages));
        if (sheet) {
            const top =
                sheet.element.getBoundingClientRect().top -
                this.scroll.getBoundingClientRect().top;
            this.scroll.scrollTop += top - 12;
        }
    },
});

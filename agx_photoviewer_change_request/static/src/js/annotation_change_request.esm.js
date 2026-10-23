/** @odoo-module **/

import {
    AnnotationEditor,
    htmlElement,
} from "@agx_photoviewer_annotation/js/annotation_renderer";
import {
    CHANGED_EVENT,
    STATE_LABELS,
    formatDate,
} from "@agx_change_request/js/change_request_panel.esm";
import {EventBus} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {jsonrpc} from "@web/core/network/rpc_service";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";
import {sprintf} from "@web/core/utils/strings";

const OUTSTANDING = ["open", "answered"];

const rpcBus = new EventBus();
let rpcId = 0;

function callRequest(method, args) {
    return jsonrpc(
        {bus: rpcBus},
        rpcId++,
        `/web/dataset/call_kw/change.request/${method}`,
        {
            model: "change.request",
            method,
            args,
            kwargs: {context: session.user_context},
        }
    );
}

function button(className, text, onClick) {
    const element = htmlElement("button", `btn btn-sm ${className}`, text);
    element.type = "button";
    element.addEventListener("click", onClick);
    return element;
}

// The pin to show once the viewer opens its file (see showPin).
let pendingFocus = null;

export function focusOnOpen(attachmentId, annotationId) {
    pendingFocus = {attachmentId, annotationId};
}

patch(AnnotationEditor.prototype, "agx_photoviewer_change_request", {
    reset() {
        this._super(...arguments);
        this.requestCheckbox = null;
        this.assigneeInputs = null;
    },

    async start() {
        await this._super(...arguments);
        const focus = pendingFocus;
        if (focus && focus.attachmentId === this.attachment.id && this.root) {
            pendingFocus = null;
            this.requestsOpen = true;
            this.renderRequests();
            this.focusAnnotation(focus.annotationId);
        }
    },

    // ------------------------------------------------------------ toolbar

    buildToolbar() {
        const toolbar = this._super(...arguments);
        if (this.data.can_request || (this.data.requests || []).length) {
            this.requestsButton = button("btn-light", "", () => this.toggleRequests());
            this.requestsButton.title = _t("Change requests");
            toolbar.append(this.requestsButton);
        }
        return toolbar;
    },

    buildDom() {
        this._super(...arguments);
        this.requestsPanel = htmlElement("div", "o_agx_annotation_requests");
        this.body.append(this.requestsPanel);
        // Open by default when some are outstanding; kept across revisions.
        if (this.requestsOpen === undefined) {
            this.requestsOpen = Boolean((this.data.requests || []).length);
        }
        this.renderRequests();
    },

    // ------------------------------------------------------------ marks

    shape(annotation) {
        const group = this._super(...arguments);
        if (annotation.request) {
            group.classList.add(
                "o_agx_annotation_request",
                `o_agx_annotation_request_${annotation.request.state}`
            );
        }
        return group;
    },

    annotationValues(values) {
        const result = this._super(...arguments);
        if (values.kind === "comment" && "change_request" in values) {
            result.change_request = Boolean(values.change_request);
            result.assignee_ids = values.assignee_ids || [];
        }
        return result;
    },

    editComment(annotation) {
        this._super(...arguments);
        // Only the files of a document taking Change requests carry them.
        if (!this.data.can_request) {
            return;
        }
        const actions = this.popover.querySelector(".o_agx_annotation_popover_actions");
        const label = htmlElement("label", "o_agx_annotation_request_toggle");
        const checkbox = htmlElement("input");
        checkbox.type = "checkbox";
        // A plain Comment unless the reviewer asks for a fix.
        checkbox.checked = Boolean(annotation.request);
        label.append(checkbox, htmlElement("span", "ms-1", _t("Ask for a fix")));
        actions.before(label);
        this.requestCheckbox = checkbox;

        // Assignees: the record's followers, and whoever it is assigned to.
        const assigned = annotation.request ? annotation.request.assignees : [];
        const users = [...assigned];
        for (const user of this.data.assignee_suggestions || []) {
            if (!users.some((u) => u.id === user.id)) {
                users.push(user);
            }
        }
        this.assigneeInputs = [];
        if (users.length) {
            const box = htmlElement("div", "o_agx_annotation_request_assignees");
            box.append(htmlElement("div", "text-muted", _t("Assign to")));
            for (const user of users) {
                const row = htmlElement("label", "d-flex align-items-center");
                const input = htmlElement("input");
                input.type = "checkbox";
                input.value = user.id;
                input.checked = assigned.some((u) => u.id === user.id);
                row.append(input, htmlElement("span", "ms-1", user.name));
                box.append(row);
                this.assigneeInputs.push(input);
            }
            const toggle = () => box.classList.toggle("d-none", !checkbox.checked);
            checkbox.addEventListener("change", toggle);
            toggle();
            actions.before(box);
        }
    },

    commentFormValues() {
        const values = this._super(...arguments);
        if (this.requestCheckbox) {
            values.change_request = this.requestCheckbox.checked;
            values.assignee_ids = (this.assigneeInputs || [])
                .filter((input) => input.checked)
                .map((input) => Number(input.value));
        }
        return values;
    },

    showComment(annotation) {
        this._super(...arguments);
        if (annotation.request) {
            this.popover.append(this.requestDetails(annotation.request));
        }
    },

    // A Change request is not in the Session note: each of its steps is
    // posted on its own.

    async add() {
        await this.refreshRequestsAfter(this._super(...arguments));
        const added = this.undoStack[this.undoStack.length - 1];
        if (added && added.request) {
            this.session.added.delete(added.id);
        }
    },

    async update(annotation) {
        const wasRequest = Boolean(annotation.request);
        await this.refreshRequestsAfter(this._super(...arguments));
        if (wasRequest || annotation.request) {
            this.session.changed.delete(annotation.id);
        }
    },

    async remove(annotation) {
        const wasRequest = Boolean(annotation.request);
        const removed = this.session.removed;
        await this.refreshRequestsAfter(this._super(...arguments));
        if (wasRequest) {
            this.session.removed = removed;
        }
    },

    // ------------------------------------------------------------ requests

    async refreshRequestsAfter(promise) {
        const result = await promise;
        // The requests of this file come from its layer, the others (its
        // other revisions) from the server.
        this.data.requests = [
            ...(this.data.requests || []).filter(
                (request) => request.pin.attachment_id !== this.attachment.id
            ),
            ...this.annotations
                .map((annotation) => annotation.request)
                .filter((request) => request && OUTSTANDING.includes(request.state)),
        ];
        this.renderRequests();
        this.notifyChanged();
        return result;
    },

    notifyChanged() {
        window.dispatchEvent(new CustomEvent(CHANGED_EVENT));
    },

    /**
     * Status, Response and actions of the Change request `request`.
     */
    requestDetails(request) {
        const details = htmlElement("div", "o_agx_annotation_request_details");
        details.append(
            htmlElement(
                "span",
                `o_agx_annotation_request_state o_agx_annotation_request_${request.state}`,
                sprintf(_t("Change request · %s"), STATE_LABELS[request.state])
            )
        );
        if (request.assignees.length) {
            details.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_popover_meta mt-1",
                    sprintf(
                        _t("Assigned to %s"),
                        request.assignees.map((user) => user.name).join(", ")
                    )
                )
            );
        }
        if (request.response) {
            details.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_popover_meta mt-1",
                    `${request.response_name} · ${formatDate(request.response_date)}`
                ),
                htmlElement("div", "o_agx_annotation_popover_text", request.response)
            );
        }
        const actions = htmlElement("div", "o_agx_annotation_popover_actions");
        details.append(actions);
        if (request.can_close) {
            const closed = request.state === "closed";
            actions.append(
                button("btn-link p-0", closed ? _t("Reopen") : _t("Close"), () =>
                    this.runRequest("request_set_closed", [request.id, !closed])
                )
            );
        }
        if (request.can_respond) {
            actions.append(
                button("btn-link p-0", _t("Respond"), () =>
                    this.editResponse(request, details)
                )
            );
        }
        return details;
    },

    editResponse(request, details) {
        const textarea = htmlElement("textarea", "form-control form-control-sm mt-1");
        textarea.rows = 2;
        textarea.value = request.response || "";
        textarea.placeholder = _t("Fixed in the next revision, or why not...");
        const actions = htmlElement("div", "o_agx_annotation_popover_actions");
        actions.append(
            button("btn-primary", _t("Save"), () =>
                this.runRequest("request_respond", [request.id, textarea.value])
            ),
            button("btn-secondary", _t("Cancel"), () =>
                details.replaceWith(this.requestDetails(request))
            )
        );
        const previous = details.querySelector(".o_agx_annotation_popover_actions");
        if (previous) {
            previous.remove();
        }
        details.append(textarea, actions);
        textarea.focus();
    },

    async runRequest(method, args) {
        this.applyRequest(await callRequest(method, args));
    },

    /**
     * Take in a Change request the server returned after a step.
     */
    applyRequest(saved) {
        const annotation = this.annotations.find(
            (a) => a.request && a.request.id === saved.id
        );
        if (annotation) {
            annotation.request = saved;
        }
        const requests = (this.data.requests || []).filter((r) => r.id !== saved.id);
        if (OUTSTANDING.includes(saved.state)) {
            requests.push(saved);
        }
        this.data.requests = requests;
        this.closePopover();
        this.redraw();
        this.renderRequests();
        this.notifyChanged();
    },

    toggleRequests() {
        this.requestsOpen = !this.requestsOpen;
        this.renderRequests();
    },

    /**
     * Panel of the outstanding Change requests on every revision of the file.
     */
    renderRequests() {
        if (!this.requestsPanel) {
            return;
        }
        const requests = [...(this.data.requests || [])].sort(
            (a, b) =>
                a.pin.revision_number - b.pin.revision_number ||
                a.pin.page - b.pin.page ||
                a.id - b.id
        );
        if (this.requestsButton) {
            this.requestsButton.innerHTML = '<i class="fa fa-exclamation-circle"></i>';
            if (requests.length) {
                this.requestsButton.append(
                    htmlElement("span", "ms-1", String(requests.length))
                );
            }
            this.requestsButton.classList.toggle("active", Boolean(this.requestsOpen));
        }
        this.requestsPanel.classList.toggle("d-none", !this.requestsOpen);
        const items = requests.map((request) => {
            const item = htmlElement("div", "o_agx_annotation_requests_item");
            item.classList.toggle(
                "o_agx_annotation_requests_elsewhere",
                request.pin.attachment_id !== this.attachment.id
            );
            item.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_popover_meta",
                    sprintf(
                        _t("Revision %s · page %s · %s"),
                        request.pin.revision_number,
                        request.pin.page,
                        request.author_name
                    )
                ),
                htmlElement("div", "o_agx_annotation_popover_text", request.text),
                this.requestDetails(request)
            );
            item.querySelector(".o_agx_annotation_popover_actions").prepend(
                button("btn-link p-0", _t("Show"), () => this.showRequest(request))
            );
            return item;
        });
        this.requestsPanel.replaceChildren(
            htmlElement(
                "div",
                "o_agx_annotation_requests_title",
                _t("Change requests")
            ),
            ...items
        );
        if (!items.length) {
            this.requestsPanel.append(
                htmlElement(
                    "div",
                    "o_agx_annotation_requests_empty",
                    _t("No outstanding change requests.")
                )
            );
        }
    },

    async showRequest(request) {
        if (request.pin.attachment_id !== this.attachment.id) {
            focusOnOpen(request.pin.attachment_id, request.pin.annotation_id);
            await this.switchAttachment({
                id: request.pin.attachment_id,
                name: request.pin.file_name,
                mimetype: request.pin.mimetype,
            });
            return;
        }
        this.focusAnnotation(request.pin.annotation_id);
    },

    /**
     * Scroll to the pin of the annotation `id` and open it.
     */
    focusAnnotation(id) {
        const annotation = this.annotations.find((a) => a.id === id);
        const sheet =
            annotation && this.sheets.find((s) => s.number === annotation.page);
        if (!sheet) {
            return;
        }
        const top =
            sheet.element.getBoundingClientRect().top -
            this.scroll.getBoundingClientRect().top +
            annotation.geometry.y * sheet.element.clientHeight;
        this.scroll.scrollTop += top - this.scroll.clientHeight / 3;
        this.openComment(sheet, annotation);
    },
});

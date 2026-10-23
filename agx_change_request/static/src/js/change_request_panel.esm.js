/** @odoo-module **/

import {
    Component,
    onWillStart,
    onWillUpdateProps,
    useExternalListener,
    useState,
} from "@odoo/owl";
import {AutoComplete} from "@web/core/autocomplete/autocomplete";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {deserializeDateTime, formatDateTime} from "@web/core/l10n/dates";
import {_lt, _t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

const MODEL = "change.request";
const OUTSTANDING = ["open", "answered"];

// Own terms: a bare "Open" is translated otherwise by other modules.
export const STATE_LABELS = {
    open: _lt("Request open"),
    answered: _lt("Request answered"),
    closed: _lt("Request closed"),
    cancelled: _lt("Request cancelled"),
};

// Fired on the window after a step taken outside the panel (e.g. in the
// photo viewer), so an open form refreshes its button, panel and chatter.
export const CHANGED_EVENT = "agx-change-request-changed";

export function formatDate(value) {
    return value ? formatDateTime(deserializeDateTime(value)) : "";
}

/**
 * Show the steps just posted on a record's chatter and the activities just
 * scheduled.
 */
export async function refreshChatter(env, resModel, resId) {
    if (!env.services.messaging) {
        return;
    }
    const messaging = await env.services.messaging.get();
    const thread = messaging.models.Thread.findFromIdentifyingData({
        id: resId,
        model: resModel,
    });
    if (thread) {
        thread.fetchData(["activities", "messages"]);
    }
}

/**
 * Users a Change request is assigned to: the record's followers are offered
 * as suggestions, any internal user can be searched.
 */
export class AssigneePicker extends Component {
    setup() {
        this.orm = useService("orm");
    }

    placeholder() {
        return _t("Assign to...");
    }

    selectedIds() {
        return this.props.selected.map((user) => user.id);
    }

    unselectedSuggestions() {
        const ids = this.selectedIds();
        return this.props.suggestions.filter((user) => !ids.includes(user.id));
    }

    sources() {
        return [
            {
                placeholder: _t("Loading..."),
                options: async (term) => {
                    const users = await this.orm.call("res.users", "name_search", [], {
                        name: term,
                        args: [["share", "=", false]],
                        limit: 8,
                    });
                    const ids = this.selectedIds();
                    return users
                        .filter(([id]) => !ids.includes(id))
                        .map(([id, name]) => ({id, label: name}));
                },
            },
        ];
    }

    add(user) {
        this.props.onChange([...this.props.selected, user]);
    }

    onSelect(option) {
        this.add({id: option.id, name: option.label});
    }

    remove(user) {
        this.props.onChange(this.props.selected.filter((u) => u.id !== user.id));
    }
}
AssigneePicker.template = "agx_change_request.AssigneePicker";
AssigneePicker.components = {AutoComplete};
AssigneePicker.props = {
    selected: Array,
    suggestions: Array,
    onChange: Function,
};

/**
 * Side panel listing the Change requests of a record: make, edit, assign,
 * answer, close and reopen them.
 */
export class ChangeRequestPanel extends Component {
    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.stateLabels = STATE_LABELS;
        this.formatDate = formatDate;
        this.state = useState({
            loaded: false,
            requests: [],
            suggestions: [],
            showAll: false,
            composer: null,
            editing: null,
            replying: null,
            historyOf: null,
        });
        onWillStart(() => this.load(this.props));
        useExternalListener(window, CHANGED_EVENT, () => this.load());
        onWillUpdateProps((next) => {
            if (
                next.resId !== this.props.resId ||
                next.resModel !== this.props.resModel
            ) {
                return this.load(next);
            }
        });
    }

    async load(props = this.props) {
        const data = await this.orm.call(MODEL, "request_load", [
            props.resModel,
            props.resId,
        ]);
        Object.assign(this.state, {
            loaded: true,
            requests: data.requests,
            suggestions: data.suggestions,
            composer: null,
            editing: null,
            replying: null,
            historyOf: null,
        });
        props.onChanged(
            data.requests.filter((request) => OUTSTANDING.includes(request.state))
                .length
        );
    }

    // ---------------------------------------------------------------- list

    isOutstanding(request) {
        return OUTSTANDING.includes(request.state);
    }

    hiddenCount() {
        return this.state.requests.filter((request) => !this.isOutstanding(request))
            .length;
    }

    /**
     * General requests first, then the pinned ones by file and page.
     */
    groups() {
        const requests = this.state.requests.filter(
            (request) => this.state.showAll || this.isOutstanding(request)
        );
        const groups = new Map();
        for (const request of requests) {
            const key = request.pin ? `pin-${request.pin.file_name}` : "general";
            if (!groups.has(key)) {
                groups.set(key, {
                    key,
                    title: request.pin ? request.pin.file_name : _t("On the document"),
                    pinned: Boolean(request.pin),
                    requests: [],
                });
            }
            groups.get(key).requests.push(request);
        }
        const result = [...groups.values()].sort(
            (a, b) => a.pinned - b.pinned || a.title.localeCompare(b.title)
        );
        for (const group of result) {
            group.requests.sort(
                (a, b) =>
                    (a.pin ? a.pin.page : 0) - (b.pin ? b.pin.page : 0) || a.id - b.id
            );
        }
        return result;
    }

    // ---------------------------------------------------------------- steps

    async run(promise) {
        await promise;
        await this.load();
        this.refreshChatter();
    }

    refreshChatter() {
        return refreshChatter(this.env, this.props.resModel, this.props.resId);
    }

    openComposer() {
        this.state.composer = {text: "", assignees: []};
    }

    create() {
        const {text, assignees} = this.state.composer;
        if (!text.trim()) {
            return;
        }
        return this.run(
            this.orm.call(MODEL, "request_create", [
                this.props.resModel,
                this.props.resId,
                text,
                assignees.map((user) => user.id),
            ])
        );
    }

    edit(request) {
        this.state.editing = {
            id: request.id,
            text: request.text,
            assignees: [...request.assignees],
        };
    }

    saveEdit() {
        const {id, text, assignees} = this.state.editing;
        return this.run(
            this.orm.call(MODEL, "request_update", [
                id,
                {text, assignee_ids: assignees.map((user) => user.id)},
            ])
        );
    }

    remove(request) {
        this.dialog.add(ConfirmationDialog, {
            body: _t(
                "Delete this change request? Its text stays in the document's chatter."
            ),
            confirm: () =>
                this.run(this.orm.call(MODEL, "request_delete", [request.id])),
            cancel: () => {
                // Just close the dialog.
            },
        });
    }

    reply(request) {
        this.state.replying = {id: request.id, text: ""};
    }

    saveReply() {
        const {id, text} = this.state.replying;
        if (!text.trim()) {
            return;
        }
        return this.run(this.orm.call(MODEL, "request_reply", [id, text]));
    }

    setClosed(request, closed) {
        return this.run(
            this.orm.call(MODEL, "request_set_closed", [request.id, closed])
        );
    }

    toggleHistory(request) {
        this.state.historyOf = this.state.historyOf === request.id ? null : request.id;
    }

    /**
     * Show the pin of a pinned request on its file; see
     * agx_photoviewer_change_request.
     */
    showPin() {
        // Only pinned requests offer it, and they need the photo viewer.
    }
}
ChangeRequestPanel.template = "agx_change_request.Panel";
ChangeRequestPanel.components = {AssigneePicker};
ChangeRequestPanel.props = {
    resModel: String,
    resId: Number,
    onChanged: Function,
    onClose: Function,
};

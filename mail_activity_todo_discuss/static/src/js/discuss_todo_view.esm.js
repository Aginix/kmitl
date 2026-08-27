/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { useService, useBus } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";

const { useState, useEffect } = owl;
const { DateTime } = luxon;

// Persist the "group by activity type" toggle across sessions so the user's
// preferred layout sticks. Off by default? No — grouping is the whole point of
// this view (a long flat inbox is what users complained about), so default on.
const GROUPED_STORAGE_KEY = "mail_activity_todo_discuss.grouped";

/**
 * The Todo inbox rendered in the Discuss MAIN content pane (when
 * discuss.isTodoActive). Lists the current user's open Todos with their detail
 * fields (capped at 100 by res.users.get_my_todos), optionally filtered to one
 * source app via discuss.todoResModel (set by the sidebar groups). Clicking a
 * Todo opens its source document; the header/footer link opens the full Todo
 * app for the remainder.
 *
 * Registered as a messaging component so the patched mail.Discuss.content
 * template can reference <DiscussTodoView/> with no import.
 */
export class DiscussTodoView extends LegacyComponent {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            todos: [],
            totalCount: 0,
            loaded: false,
            // Free-text filter applied client-side over the fetched list.
            search: "",
            // Group the list by activity type (ประเภทกิจกรรม) when true.
            grouped: browser.localStorage.getItem(GROUPED_STORAGE_KEY) !== "false",
            // Per-group collapse state, keyed by group label, so the user can
            // fold away every type but the one they want to focus on.
            collapsed: {},
        });

        // Fetch on mount and whenever the source-app filter or the inbox/history
        // mode changes (the deps read discuss.todoResModel / isTodoHistory, which
        // the template also reads, so useModels re-renders and this effect
        // re-runs on a sidebar group / History click).
        useEffect(
            () => {
                this.fetchData();
            },
            () => [this.discuss.todoResModel, this.discuss.isTodoHistory]
        );
        useBus(this.env.bus, "mail_activity_todo_updated", () => this.fetchData());
    }

    get discuss() {
        return this.props.record.discuss;
    }

    get filterLabel() {
        // Load-bearing: this read of discuss.todoResModel (evaluated every render
        // via the header's t-if="filterLabel") is what subscribes useModels to
        // the field, so openTodos(resModel) re-renders and the useEffect refetch
        // fires. Keep reading todoResModel here unconditionally.
        if (!this.discuss.todoResModel) {
            return "";
        }
        return this.state.todos.length
            ? this.state.todos[0].app
            : this.discuss.todoResModel;
    }

    /**
     * The fetched Todos narrowed by the search box (case-insensitive substring
     * over the fields a user would scan for: activity type, summary, source
     * record/app, assignee and note). Empty query returns everything.
     */
    get filteredTodos() {
        const query = this.state.search.trim().toLowerCase();
        if (!query) {
            return this.state.todos;
        }
        return this.state.todos.filter((todo) =>
            [
                todo.activity_type,
                todo.summary,
                todo.res_name,
                todo.app,
                todo.assigned,
                todo.note,
            ].some((value) => value && value.toLowerCase().includes(query))
        );
    }

    /**
     * The filtered Todos bucketed by activity type, preserving the incoming
     * (newest-first) order within each bucket. Todos with no activity type fall
     * into a trailing "Other" group. Returns an array of
     * {label, todos, collapsed} for the grouped template.
     */
    get todoGroups() {
        const otherLabel = this.env._t("Other");
        const byLabel = new Map();
        for (const todo of this.filteredTodos) {
            const label = todo.activity_type || otherLabel;
            if (!byLabel.has(label)) {
                byLabel.set(label, []);
            }
            byLabel.get(label).push(todo);
        }
        return [...byLabel.entries()].map(([label, todos]) => ({
            label,
            todos,
            collapsed: !!this.state.collapsed[label],
        }));
    }

    /** Toggle grouping and remember the choice for next time. */
    toggleGrouped() {
        this.state.grouped = !this.state.grouped;
        browser.localStorage.setItem(GROUPED_STORAGE_KEY, this.state.grouped);
    }

    /** Fold/unfold a single activity-type group. */
    toggleGroup(label) {
        this.state.collapsed[label] = !this.state.collapsed[label];
    }

    clearSearch() {
        this.state.search = "";
    }

    /**
     * Locale-aware "created X ago" for the meta line, e.g. "3 hours ago".
     * create_date is a UTC datetime string; deserializeDateTime lands it in the
     * user's timezone. Returns "" when absent/unparseable so the line hides.
     */
    createdAgo(todo) {
        if (!todo.create_date) {
            return "";
        }
        return deserializeDateTime(todo.create_date).toRelative() || "";
    }

    /** Exact created datetime for the meta-line tooltip. */
    createdTooltip(todo) {
        if (!todo.create_date) {
            return "";
        }
        return formatDateTime(deserializeDateTime(todo.create_date));
    }

    /** Locale-aware "completed X ago" for completed (done) history rows. */
    completedAgo(todo) {
        if (!todo.completed_date) {
            return "";
        }
        return deserializeDateTime(todo.completed_date).toRelative() || "";
    }

    /** Exact completed datetime for the meta-line tooltip. */
    completedTooltip(todo) {
        if (!todo.completed_date) {
            return "";
        }
        return formatDateTime(deserializeDateTime(todo.completed_date));
    }

    /**
     * Deadline as a human countdown plus its urgency styling. Uses
     * toRelativeCalendar ("today"/"tomorrow"/"in 3 days"/"yesterday") — the
     * calendar form is correct for date-only deadlines, unlike toRelative which
     * would measure from midnight. Colour/icon follow the server-computed state
     * (overdue/today/planned), with planned deadlines within two days flagged
     * as imminent. Returns null when there is no deadline.
     */
    deadlineInfo(todo) {
        if (!todo.date_deadline) {
            return null;
        }
        const dt = deserializeDate(todo.date_deadline);
        const info = {
            label: dt.toRelativeCalendar() || "",
            exact: formatDate(dt),
            className: "text-muted",
            icon: "fa-clock-o",
        };
        if (todo.state === "overdue") {
            info.className = "text-danger fw-bold";
            info.icon = "fa-exclamation-circle";
        } else if (todo.state === "today") {
            info.className = "text-warning fw-bold";
            info.icon = "fa-hourglass-half";
        } else {
            const days = dt
                .startOf("day")
                .diff(DateTime.now().startOf("day"), "days").days;
            if (days <= 2) {
                info.className = "text-warning";
                info.icon = "fa-hourglass-start";
            }
        }
        return info;
    }

    async fetchData() {
        try {
            const resModel = this.discuss.todoResModel || false;
            const result = await this.orm.call(
                "res.users",
                "get_my_todos",
                [resModel],
                { read: this.discuss.isTodoHistory }
            );
            this.state.todos = result.todos || [];
            this.state.totalCount = result.total_count || 0;
        } catch (error) {
            console.error("Failed to fetch Todos:", error);
            this.state.todos = [];
            this.state.totalCount = 0;
        } finally {
            // Latches true after the first fetch so the empty-state never
            // flashes before data arrives (and refetches keep the current list
            // visible rather than blanking).
            this.state.loaded = true;
        }
    }

    onShowAll() {
        // Stay on the Todo page, drop the per-app filter.
        this.discuss.openTodos();
    }

    onTodoClick(todo) {
        // Open the Todo's source record. Build the act_window client-side with
        // an explicit `views` (the action service requires it).
        if (!todo.res_model || !todo.res_id) {
            return;
        }
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: todo.res_model,
                res_id: todo.res_id,
                views: [[false, "form"]],
                target: "current",
            },
            // Clear the breadcrumb trail so repeated Todo → record → systray →
            // Todo hops don't stack endlessly (Discuss/รายการงาน/record/... ad
            // infinitum). Each Todo click starts a fresh trail at the record;
            // the systray reopens Todos when the user wants to go back.
            { clearBreadcrumbs: true }
        );
    }

    onViewAllClick() {
        this.action.doAction("mail_activity_todo.action_my_todos");
    }
}

Object.assign(DiscussTodoView, {
    props: { record: Object },
    template: "mail_activity_todo_discuss.DiscussTodoView",
});

registerMessagingComponent(DiscussTodoView);

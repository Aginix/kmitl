/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { evalDomain } from "@web/views/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";

// Budget reservation field widget (วิดเจ็ตจองงบประมาณ): one consolidated control
// that manages a budget reservation AND displays the picked รหัสงบประมาณ + the
// accounting dimensions + the control-node budget standing (งบที่จองได้), so the
// form reflects the budget status without opening the picker.
//
// Anchored on the host's budget-account field (default budget_account_id); the
// fiscal-year, distribution and intended-amount fields are named via options:
//   <field name="budget_account_id" widget="budget_reservation"
//          options="{'fiscal_year_field': 'account_fiscal_year_id',
//                    'distribution_field': 'analytic_distribution',
//                    'amount_field': 'budget_amount', 'show_status': true}"/>
//
// Selection is delegated to the existing reservation picker, opened in
// return_selection mode: it hands the choice back via onClose and the widget does
// an in-memory record.update of all three fields, persisted on the host's own
// Save — no server write, no forced reload (ADR-0009).
export class BudgetReservationField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ status: null, loading: false });
        onWillStart(() => this.loadStatus(this.props));
        onWillUpdateProps((nextProps) => {
            if (this._selectionChanged(this.props, nextProps)) {
                this.loadStatus(nextProps);
            }
        });
    }

    // --- option-driven sibling field names ---
    get fiscalYearField() {
        return this.props.fiscalYearField || "account_fiscal_year_id";
    }
    get distributionField() {
        return this.props.distributionField || "analytic_distribution";
    }
    get amountField() {
        return this.props.amountField || "budget_amount";
    }
    get showStatus() {
        return this.props.showStatus;
    }

    // Whether the status figures are shown. The optional status_invisible option
    // is a domain evaluated against the record exactly like an attrs invisible
    // modifier — the figures are hidden when it matches. The code and dimensions
    // are always shown regardless.
    get statusVisible() {
        if (!this.showStatus || !this.state.status || !this.fiscalYear) {
            return false;
        }
        if (this.props.statusInvisible) {
            return !evalDomain(
                this.props.statusInvisible,
                this.props.record.evalContext
            );
        }
        return true;
    }

    // --- current values off the in-memory record ---
    get account() {
        return this.props.value; // [id, display_name] or false
    }
    get fiscalYear() {
        return this.props.record.data[this.fiscalYearField] || false;
    }
    get amount() {
        const value = this.props.record.data[this.amountField];
        return typeof value === "number" ? value : 0;
    }
    get status() {
        return this.state.status;
    }
    get dimensions() {
        const dims = (this.state.status && this.state.status.dimensions) || [];
        // Ownership-tag dimensions (kmitl_project / procurement_plan) are shown
        // only when the host opts in (show_pool_dimensions); they are never part
        // of the availability figures.
        return this.props.showPoolDimensions
            ? dims
            : dims.filter((dim) => !dim.is_pool);
    }
    get loading() {
        return this.state.loading;
    }

    _fyId(props) {
        const fy = props.record.data[this.fiscalYearField];
        return fy ? fy[0] : false;
    }

    _selectionChanged(prev, next) {
        const accountChanged =
            (prev.value && prev.value[0]) !== (next.value && next.value[0]);
        const fyChanged = this._fyId(prev) !== this._fyId(next);
        const distChanged =
            JSON.stringify(prev.record.data[this.distributionField] || {}) !==
            JSON.stringify(next.record.data[this.distributionField] || {});
        // Re-fetch on state change too: figures fetched in draft are pre-reserve,
        // so the post-reserve standing must be refreshed when the host enters a
        // state that displays the status (e.g. draft → new).
        const stateChanged = prev.record.data.state !== next.record.data.state;
        return accountChanged || fyChanged || distChanged || stateChanged;
    }

    async loadStatus(props) {
        const account = props.value;
        if (!account) {
            this.state.status = null;
            return;
        }
        this.state.loading = true;
        try {
            this.state.status = await this.orm.call(
                "budget.controller",
                "get_reservation_status",
                [
                    account[0],
                    props.record.data[this.distributionField] || {},
                    this._fyId(props),
                ]
            );
        } finally {
            this.state.loading = false;
        }
    }

    // Sufficiency vs the host's intended reserve amount — the hard reserve-time
    // check (amount > available → blocked at draft→new). Computed client-side so
    // it tracks edits to the amount field without another round-trip.
    get sufficient() {
        if (!this.state.status || !this.amount) {
            return null;
        }
        return this.amount <= this.state.status.available;
    }
    get shortage() {
        return this.state.status ? this.amount - this.state.status.available : 0;
    }

    format(value) {
        return (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    async openPicker() {
        if (this.props.readonly) {
            return;
        }
        const record = this.props.record;
        // Approach S (ADR-0009): action_open_reservation_picker is an instance
        // method that reads self to build the account domain + dimension/FY
        // defaults, so the record must be persisted first — the same precondition
        // the legacy picker button (type="object") already imposed.
        if (record.isDirty || !record.resId) {
            const saved = await record.save();
            if (!saved) {
                return;
            }
        }
        const action = await this.orm.call(
            record.resModel,
            "action_open_reservation_picker",
            [[record.resId]]
        );
        // Open in return_selection mode so the picker hands the choice back.
        action.context = { ...(action.context || {}), return_selection: true };
        this.action.doAction(action, {
            onClose: (infos) => this.applySelection(infos),
        });
    }

    async applySelection(infos) {
        if (!infos || !infos.account_id) {
            return; // cancelled / closed without a selection
        }
        await this.props.record.update({
            [this.props.name]: [infos.account_id], // label resolved via name_get
            [this.distributionField]: infos.distribution || false,
            [this.fiscalYearField]: infos.fiscal_year_id
                ? [infos.fiscal_year_id]
                : false,
        });
        await this.loadStatus(this.props);
    }
}

BudgetReservationField.template = "budget.BudgetReservationField";
BudgetReservationField.supportedTypes = ["many2one"];
BudgetReservationField.props = {
    ...standardFieldProps,
    fiscalYearField: { type: String, optional: true },
    distributionField: { type: String, optional: true },
    amountField: { type: String, optional: true },
    showStatus: { type: Boolean, optional: true },
    statusInvisible: { type: [Array, Boolean], optional: true },
    showPoolDimensions: { type: Boolean, optional: true },
};
BudgetReservationField.extractProps = ({ attrs }) => {
    const options = attrs.options || {};
    return {
        fiscalYearField: options.fiscal_year_field,
        distributionField: options.distribution_field,
        amountField: options.amount_field,
        // Status block shown unless explicitly disabled.
        showStatus: options.show_status !== false,
        // Optional domain (attrs-invisible semantics): hide the status figures
        // when it matches the record.
        statusInvisible: options.status_invisible,
        // Also display the ownership-tag dimensions (kmitl_project /
        // procurement_plan), off by default.
        showPoolDimensions: options.show_pool_dimensions === true,
    };
};

registry.category("fields").add("budget_reservation", BudgetReservationField);

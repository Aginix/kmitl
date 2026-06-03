/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { formatMonetary } from "@web/views/fields/formatters";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

/**
 * Read-only field widget that renders the current budget status (six
 * dashboard-aligned figures) for the (fiscal year, budget account, analytic
 * dimensions) combination selected on the record.
 *
 * It is bound to the analytic distribution field but reads two sibling fields
 * as well; field names are configurable through ``options``:
 *   - fiscal_year_field   (default: account_fiscal_year_id, optional on record)
 *   - account_field       (default: budget_account_id)
 *   - distribution_field  (default: the bound field)
 *
 * Reactivity follows the core ``domain`` field widget: the form re-renders
 * every field on each record change, so ``onWillUpdateProps`` fires whenever
 * any of the three fields change.
 */
export class BudgetStatusCard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: false, error: false, data: null });
        this._lastKey = null;
        this._seq = 0;
        this._debouncedLoad = debounce((payload) => this._load(payload), 250);

        onWillStart(() => this._fetch(this.props, true));
        onWillUpdateProps((nextProps) => this._fetch(nextProps, false));
    }

    get fiscalYearField() {
        return this.props.fiscalYearField;
    }
    get accountField() {
        return this.props.accountField;
    }
    get distributionField() {
        return this.props.distributionField;
    }

    /** Read a record field value as a scalar id (m2o -> id) or false. */
    _scalar(props, fieldName) {
        if (!fieldName) {
            return false;
        }
        const value = props.record.data[fieldName];
        if (Array.isArray(value)) {
            return value[0] || false;
        }
        return value || false;
    }

    _payload(props) {
        return {
            fyId: this._scalar(props, this.fiscalYearField),
            accId: this._scalar(props, this.accountField),
            dist: props.record.data[this.distributionField] || {},
        };
    }

    /**
     * Decide whether to (re)load. Guards against the many redundant re-renders
     * a single edit triggers via ``model.notify()``: only acts when the
     * (fiscal year, account, distribution) key actually changed.
     */
    _fetch(props, immediate) {
        const payload = this._payload(props);
        const key = JSON.stringify([payload.fyId, payload.accId, payload.dist]);
        if (key === this._lastKey) {
            return;
        }
        this._lastKey = key;

        if (!payload.accId) {
            // No budget account selected: empty state, no server round-trip.
            this._seq++;
            this.state.loading = false;
            this.state.error = false;
            this.state.data = null;
            return;
        }

        this.state.loading = true;
        if (immediate) {
            this._load(payload);
        } else {
            this._debouncedLoad(payload);
        }
    }

    async _load(payload) {
        const seq = ++this._seq;
        this.state.loading = true;
        this.state.error = false;
        try {
            const data = await this.orm.call("budget.controller", "get_budget_card", [
                payload.fyId || false,
                payload.accId,
                payload.dist,
            ]);
            if (seq !== this._seq) {
                return; // a newer request superseded this one
            }
            this.state.data = data;
        } catch (_e) {
            if (seq !== this._seq) {
                return;
            }
            this.state.error = true;
        } finally {
            if (seq === this._seq) {
                this.state.loading = false;
            }
        }
    }

    formatAmount(value) {
        const currencyId = this.state.data && this.state.data.currency_id;
        return formatMonetary(value || 0, { currencyId });
    }
}

BudgetStatusCard.template = "budget.BudgetStatusCard";
BudgetStatusCard.props = {
    ...standardFieldProps,
    fiscalYearField: { type: String, optional: true },
    accountField: { type: String, optional: true },
    distributionField: { type: String, optional: true },
};
BudgetStatusCard.supportedTypes = ["json"];
BudgetStatusCard.isEmpty = () => false;
BudgetStatusCard.extractProps = ({ attrs }) => ({
    fiscalYearField: attrs.options.fiscal_year_field || "account_fiscal_year_id",
    accountField: attrs.options.account_field || "budget_account_id",
    distributionField: attrs.options.distribution_field || attrs.name,
});

registry.category("fields").add("budget_status_card", BudgetStatusCard);

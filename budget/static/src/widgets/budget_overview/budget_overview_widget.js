/** @odoo-module **/

import { Component, onWillStart, useState, onWillUpdateProps, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    getMany2oneId,
    formatThaiCurrency,
    buildAnalyticData,
    allDimensionsFilled,
} from "@budget/utils/budget_utils";

export class BudgetOverviewWidget extends Component {
    setup() {
        this.orm = useService("orm");

        this.state = useState({
            data: null,
            loading: false,
            error: null,
        });

        this._lastKey = null;
        this._debounceTimer = null;

        onWillStart(() => this._fetchIfReady(this.props));

        onWillUpdateProps((nextProps) => {
            const key = this._buildKey(nextProps);
            if (key !== this._lastKey) {
                this._debouncedFetch(nextProps);
            }
        });

        onWillDestroy(() => clearTimeout(this._debounceTimer));
    }

    _buildKey(props) {
        const data = buildAnalyticData(props.record.data);
        if (!allDimensionsFilled(data)) return null;
        const fy = getMany2oneId(props.record.data, "account_fiscal_year_id");
        return JSON.stringify({ ...data, fiscal_year_id: fy });
    }

    _debouncedFetch(props) {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => this._fetchIfReady(props), 300);
    }

    async _fetchIfReady(props) {
        const recordData = props.record.data;
        const data = buildAnalyticData(recordData);

        if (!allDimensionsFilled(data)) {
            this.state.data = null;
            this.state.error = null;
            this._lastKey = null;
            return;
        }

        const key = this._buildKey(props);
        this._lastKey = key;

        const fiscalYearId = getMany2oneId(recordData, "account_fiscal_year_id");

        try {
            this.state.loading = true;
            this.state.error = null;

            const result = await this.orm.call(
                "budget.controller",
                "get_budget_status_for_widget",
                [data, fiscalYearId || false]
            );

            if (this._lastKey !== key) return;

            if (result.error === "no_fiscal_year") {
                this.state.error = "ไม่พบปีงบประมาณปัจจุบัน";
                this.state.data = null;
            } else {
                this.state.data = result;
                this.state.error = null;
            }
        } catch (e) {
            if (this._lastKey === key) {
                this.state.error = "ไม่สามารถโหลดข้อมูลงบประมาณได้";
                this.state.data = null;
            }
        } finally {
            if (this._lastKey === key) {
                this.state.loading = false;
            }
        }
    }

    formatCurrency(amount) {
        return formatThaiCurrency(amount);
    }

    get hasData() {
        return !!this.state.data && !this.state.data.error;
    }

    get utilizationPercent() {
        if (!this.state.data) return 0;
        return Math.min(this.state.data.utilization_percentage || 0, 100);
    }

    get utilizationBarClass() {
        if (this.state.data && this.state.data.is_over_budget) return "bg-danger";
        if (this.utilizationPercent >= 80) return "bg-warning";
        return "bg-success";
    }
}

BudgetOverviewWidget.template = "budget.BudgetOverviewWidget";

registry.category("view_widgets").add("budget_overview", BudgetOverviewWidget);

/** @odoo-module **/

import { Component, onWillStart, useState, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

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

        onWillStart(async () => {
            await this._fetchIfReady();
        });

        onWillUpdateProps(async (nextProps) => {
            const key = this._getKey(nextProps);
            if (key !== this._lastKey) {
                this._debouncedFetch(nextProps);
            }
        });
    }

    _getFieldValue(fieldName, props) {
        const p = props || this.props;
        const val = p.record.data[fieldName];
        if (!val) return false;
        return val[0] || val.id || false;
    }

    _getAnalyticData(props) {
        return {
            account_id: this._getFieldValue("budget_account_id", props),
            activity_analytic_id: this._getFieldValue("activity_analytic_id", props),
            department_analytic_id: this._getFieldValue("department_analytic_id", props),
            fund_analytic_id: this._getFieldValue("fund_analytic_id", props),
            source_analytic_id: this._getFieldValue("source_analytic_id", props),
        };
    }

    _allDimensionsFilled(props) {
        const data = this._getAnalyticData(props);
        return (
            data.account_id &&
            data.activity_analytic_id &&
            data.department_analytic_id &&
            data.fund_analytic_id &&
            data.source_analytic_id
        );
    }

    _getKey(props) {
        if (!this._allDimensionsFilled(props)) return null;
        const data = this._getAnalyticData(props);
        const fy = this._getFieldValue("account_fiscal_year_id", props);
        return JSON.stringify({ ...data, fiscal_year_id: fy });
    }

    _debouncedFetch(props) {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => this._fetchIfReady(props), 300);
    }

    async _fetchIfReady(props) {
        if (!this._allDimensionsFilled(props)) {
            this.state.data = null;
            this.state.error = null;
            this._lastKey = null;
            return;
        }

        const key = this._getKey(props);
        this._lastKey = key;

        const analyticData = this._getAnalyticData(props);
        const fiscalYearId = this._getFieldValue("account_fiscal_year_id", props);

        try {
            this.state.loading = true;
            this.state.error = null;

            const result = await this.orm.call(
                "budget.controller",
                "get_budget_status_for_widget",
                [analyticData, fiscalYearId || false]
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
        return Number(amount || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    get hasData() {
        return !!this.state.data && !this.state.data.error;
    }

    get utilizationPercent() {
        if (!this.state.data) return 0;
        return Math.min(this.state.data.utilization_percentage || 0, 100);
    }

    get utilizationBarClass() {
        const pct = this.utilizationPercent;
        if (this.state.data && this.state.data.is_over_budget) return "bg-danger";
        if (pct >= 80) return "bg-warning";
        return "bg-success";
    }
}

BudgetOverviewWidget.template = "budget.BudgetOverviewWidget";

registry.category("view_widgets").add("budget_overview", BudgetOverviewWidget);

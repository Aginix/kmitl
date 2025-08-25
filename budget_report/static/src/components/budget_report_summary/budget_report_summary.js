/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {DepartmentFilter} from "../department_filter/department_filter";

export class BudgetReportSummary extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false
        };

        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
                source_analytic_id: null,
                department_ids: [],
            },
            loading: false,
            rows: [],
            fiscalYear: null,
            sourceAnalytic: null,
            departments: null,
            selectedDepartmentIds: [],
            showSidebar: true,
            filterOptions: {
                fiscal_years: [],
                departments: [],
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const response = await this.orm.call(
                "budget.report.summary",
                "get_data",
                [this.state.filters]
            );

            this.state.rows = response.rows;
            this.state.fiscalYear = response.fiscal_year;
            this.state.sourceAnalytic = response.source_analytic;
            this.state.filters = response.filters;
            this.state.departments = response.departments || null;

            this.state.filterOptions = await this.orm.call(
                "budget.report.summary",
                "get_filter_options",
                []
            );
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this.loadData()
    }

    onPrint() {}

    get departments() {
        return this.state.departments;
    }

    get rows() {
        return this.state.rows
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }

    async onFilterChange() {
        await this.loadData()
    }

    async onFiscalYearChange(e) {
        this.onChangeBy('fiscal_year_id', e.target.value ? Number(e.target.value) : null)
    }

    async onChangeBy(name, value) {
        this.state.filters[name] = value
        await this.onFilterChange();
    }

    async onSourceAnalyticIdChange(e) {
        this.onChangeBy('source_analytic_id', e.target.value ? Number(e.target.value) : null)
    }

    onDepartmentSelectionChange(selectedIds) {
        this.state.selectedDepartmentIds = selectedIds;
        this.state.filters.department_ids = selectedIds;
        this.loadData();
    }

    get departmentHierarchy() {
        return this.state.filterOptions.departments || [];
    }
}

BudgetReportSummary.template = "budget_report.BudgetReportSummary";
BudgetReportSummary.components = {
    ControlPanel,
    DepartmentFilter
};

registry
    .category("actions")
    .add("budget_report_summary", BudgetReportSummary);

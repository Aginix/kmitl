/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class BudgetAppropriationDashboard extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false
        };

        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
            },
            loading: false,
            data: {},
            fiscalYear: null,
            filterOptions: {
                fiscal_years: [],
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const response = await this.rpc("/budget_appropriation/dashboard/data", {
                fiscal_year_id: this.state.filters.fiscal_year_id,
            });

            this.state.filterOptions = response.filter_options;
            this.state.filters = response.filters;
            this.state.fiscalYear = response.fiscal_year;
            this.state.data = response.data;
        } catch (error) {
            console.error("Error loading data:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async onFiscalYearChange(e) {
        const fiscalYearId = e.target.value ? Number(e.target.value) : null;
        this.state.filters.fiscal_year_id = fiscalYearId;
        await this.loadData();
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.filters.fiscal_year_id;
    }

    get selectedFiscalYear() {
        return this.state.fiscalYear ? this.state.fiscalYear.name : "";
    }
}

BudgetAppropriationDashboard.template = "budget_appropriation_report.BudgetAppropriationDashboard";
BudgetAppropriationDashboard.components = {
    ControlPanel
};

registry
    .category("actions")
    .add("budget_appropriation_dashboard", BudgetAppropriationDashboard);

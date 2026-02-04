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

        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            filters: {
                fiscal_year_id: null,
            },
            loading: false,
            filterOptions: {
                fiscal_years: [],
            },
        });

        onWillStart(async () => {
            await this.loadFilterOptions();
        });
    }

    async loadFilterOptions() {
        this.state.loading = true;
        try {
            const fiscalYears = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["id", "name"],
                {order: "date_from desc"}
            );
            this.state.filterOptions.fiscal_years = fiscalYears;

            if (fiscalYears.length > 0) {
                this.state.filters.fiscal_year_id = fiscalYears[0].id;
            }
        } catch (error) {
            console.error("Error loading filter options:", error);
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
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.filters.fiscal_year_id;
    }

    get selectedFiscalYear() {
        const fy = this.state.filterOptions.fiscal_years.find(
            (f) => f.id === this.state.filters.fiscal_year_id
        );
        return fy ? fy.name : "";
    }
}

BudgetAppropriationDashboard.template = "budget_appropriation_report.BudgetAppropriationDashboard";
BudgetAppropriationDashboard.components = {
    ControlPanel
};

registry
    .category("actions")
    .add("budget_appropriation_dashboard", BudgetAppropriationDashboard);

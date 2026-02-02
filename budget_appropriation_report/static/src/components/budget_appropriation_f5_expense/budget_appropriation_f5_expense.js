/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BudgetAppropriationF5Expense extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-left": true,
            "bottom-right": false,
        };

        this.state = useState({
            loading: true,
            error: null,
            filters: {
                fiscal_year_id: null,
                source_analytic_id: null,
            },
            filterOptions: {
                fiscal_years: [],
                sources: [],
            },
            appropriations: [],  // Now hierarchical structure
            selected_appropriation_ids: [],
            expanded_departments: [],  // Track expanded department IDs
            sidebarWidth: 320,  // Default sidebar width
        });

        this.orm = useService("orm");
        this.notification = useService("notification");

        // Sidebar resize
        this.sidebarRef = useRef("sidebar");
        this.isResizing = false;

        // Bind resize handlers
        this._onMouseMove = this._onMouseMove.bind(this);
        this._onMouseUp = this._onMouseUp.bind(this);

        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.loadAppropriations();
        });

        onMounted(() => {
            document.addEventListener("mousemove", this._onMouseMove);
            document.addEventListener("mouseup", this._onMouseUp);
        });

        onWillUnmount(() => {
            document.removeEventListener("mousemove", this._onMouseMove);
            document.removeEventListener("mouseup", this._onMouseUp);
        });
    }

    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "budget.appropriation.f5.expense",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;

            // Set default fiscal year if available
            if (options.fiscal_years.length > 0) {
                this.state.filters.fiscal_year_id = options.fiscal_years[0].id;
            }

            // Set default source to code "2" (เงินรายได้)
            if (options.sources.length > 0) {
                const defaultSource = options.sources.find(s => s.code === "2") || options.sources[0];
                this.state.filters.source_analytic_id = defaultSource.id;
            }
        } catch (error) {
            console.error("Error loading filter options:", error);
            this.notification.add("เกิดข้อผิดพลาดในการโหลดตัวเลือกตัวกรอง", { type: "danger" });
        }
    }

    async loadAppropriations() {
        try {
            this.state.loading = true;
            this.state.error = null;

            const result = await this.orm.call(
                "budget.appropriation.f5.expense",
                "get_appropriations",
                [this.state.filters]
            );

            this.state.appropriations = result;
            // Reset selections when appropriations change
            this.state.selected_appropriation_ids = [];

        } catch (error) {
            console.error("Error loading appropriations:", error);
            this.state.error = error.message || "เกิดข้อผิดพลาดในการโหลดข้อมูล";
            this.notification.add("เกิดข้อผิดพลาดในการโหลดข้อมูล", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // ---- Getters ----

    get selectedFiscalYear() {
        if (!this.state.filters.fiscal_year_id) return null;
        return this.state.filterOptions.fiscal_years.find(
            fy => fy.id === this.state.filters.fiscal_year_id
        );
    }

    get selectedSource() {
        if (!this.state.filters.source_analytic_id) return null;
        return this.state.filterOptions.sources.find(
            source => source.id === this.state.filters.source_analytic_id
        );
    }

    get selectedAppropriationIds() {
        return this.state.selected_appropriation_ids;
    }

    get portalUrl() {
        const ids = this.state.selected_appropriation_ids;
        if (ids.length === 0) {
            return "";
        } else if (ids.length === 1) {
            return `/budget/budget_appropriation/${ids[0]}/content`;
        } else {
            return `/budget/budget_appropriation/multi/${ids.join(",")}/content`;
        }
    }

    get printUrl() {
        const ids = this.state.selected_appropriation_ids;
        if (ids.length === 0) {
            return "";
        } else if (ids.length === 1) {
            return `/budget/budget_appropriation/${ids[0]}`;
        } else {
            return `/budget/budget_appropriation/multi/${ids.join(",")}`;
        }
    }

    get hasSelection() {
        return this.state.selected_appropriation_ids.length > 0;
    }

    // ---- Event Handlers ----

    async onFiscalYearChange(e) {
        const fiscalYearId = e.target.value ? Number(e.target.value) : null;
        this.state.filters.fiscal_year_id = fiscalYearId;
        await this.loadAppropriations();
    }

    async onSourceChange(e) {
        this.state.filters.source_analytic_id = e.target.value ? Number(e.target.value) : null;
        await this.loadAppropriations();
    }

    onAppropriationToggle(id) {
        const idx = this.state.selected_appropriation_ids.indexOf(id);
        if (idx === -1) {
            this.state.selected_appropriation_ids.push(id);
        } else {
            this.state.selected_appropriation_ids.splice(idx, 1);
        }
    }

    onSelectAll() {
        const allIds = this._getAllAppropriationIdsFromTree(this.state.appropriations);
        this.state.selected_appropriation_ids = allIds;
    }

    onDeselectAll() {
        this.state.selected_appropriation_ids = [];
    }

    onRefresh() {
        this.loadAppropriations();
    }

    onPrint() {
        if (this.hasSelection) {
            window.open(this.printUrl, '_blank');
        }
    }

    // ---- Department Tree Methods ----

    onToggleDepartment(deptId) {
        const idx = this.state.expanded_departments.indexOf(deptId);
        if (idx === -1) {
            this.state.expanded_departments.push(deptId);
        } else {
            this.state.expanded_departments.splice(idx, 1);
        }
    }

    isDepartmentExpanded(deptId) {
        return this.state.expanded_departments.includes(deptId);
    }

    onSelectDepartment(dept) {
        const appIds = this._getAllAppropriationIds(dept);
        const allSelected = appIds.every(id => this.state.selected_appropriation_ids.includes(id));

        if (allSelected) {
            // Deselect all
            this.state.selected_appropriation_ids =
                this.state.selected_appropriation_ids.filter(id => !appIds.includes(id));
        } else {
            // Select all
            const newIds = [...this.state.selected_appropriation_ids];
            appIds.forEach(id => {
                if (!newIds.includes(id)) newIds.push(id);
            });
            this.state.selected_appropriation_ids = newIds;
        }
    }

    _getAllAppropriationIds(dept) {
        const ids = (dept.appropriations || []).map(a => a.id);
        for (const child of (dept.children || [])) {
            ids.push(...this._getAllAppropriationIds(child));
        }
        return ids;
    }

    _getAllAppropriationIdsFromTree(depts) {
        const ids = [];
        for (const dept of depts) {
            ids.push(...this._getAllAppropriationIds(dept));
        }
        return ids;
    }

    isDepartmentSelected(dept) {
        const appIds = this._getAllAppropriationIds(dept);
        return appIds.length > 0 && appIds.every(id => this.state.selected_appropriation_ids.includes(id));
    }

    isDepartmentPartiallySelected(dept) {
        const appIds = this._getAllAppropriationIds(dept);
        const selectedCount = appIds.filter(id => this.state.selected_appropriation_ids.includes(id)).length;
        return selectedCount > 0 && selectedCount < appIds.length;
    }

    onExpandAll() {
        const allDeptIds = this._getAllDepartmentIds(this.state.appropriations);
        this.state.expanded_departments = allDeptIds;
    }

    onCollapseAll() {
        this.state.expanded_departments = [];
    }

    _getAllDepartmentIds(depts) {
        const ids = [];
        for (const dept of depts) {
            ids.push(dept.id);
            if (dept.children) {
                ids.push(...this._getAllDepartmentIds(dept.children));
            }
        }
        return ids;
    }

    // ---- Helper Methods ----

    isAppropriationSelected(id) {
        return this.state.selected_appropriation_ids.includes(id);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('th-TH', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }

    // ---- Sidebar Resize Methods ----

    onResizeStart(ev) {
        ev.preventDefault();
        this.isResizing = true;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    }

    _onMouseMove(ev) {
        if (!this.isResizing) return;

        const sidebar = this.sidebarRef.el;
        if (!sidebar) return;

        const containerRect = sidebar.parentElement.getBoundingClientRect();
        const newWidth = ev.clientX - containerRect.left;

        // Constrain width between 200px and 500px
        const minWidth = 200;
        const maxWidth = 500;
        this.state.sidebarWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
    }

    _onMouseUp() {
        if (this.isResizing) {
            this.isResizing = false;
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        }
    }
}

BudgetAppropriationF5Expense.template = "budget_appropriation_report.BudgetAppropriationF5Expense";
BudgetAppropriationF5Expense.components = {
    ControlPanel
};

registry.category("actions").add("budget_appropriation_f5_expense_overview_report", BudgetAppropriationF5Expense);

/** @odoo-module */

import {Component, useState, onWillStart, onWillUpdateProps} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class DepartmentFilterSidebar extends Component {
    setup() {
        this.orm = useService("orm");

        this.state = useState({
            departments: [],
            expandedNodes: new Set(),
            searchTerm: "",
            loading: false,
        });

        onWillStart(async () => {
            await this.loadDepartments();
        });

        onWillUpdateProps(async (nextProps) => {
            // Update selection state when props change
            if (nextProps.selectedIds !== this.props.selectedIds) {
                this._updateSelectionState(
                    this.state.departments,
                    nextProps.selectedIds
                );
            }
        });
    }

    _updateSelectionState(departments, selectedIds) {
        departments.forEach((dept) => {
            dept.isSelected = selectedIds.includes(dept.id);
            if (dept.children) {
                this._updateSelectionState(dept.children, selectedIds);
            }
        });
    }

    async loadDepartments() {
        this.state.loading = true;
        try {
            // Use the departments from props if available, otherwise load from backend
            if (this.props.departments && this.props.departments.length > 0) {
                this.state.departments = this._processHierarchy(this.props.departments);
            } else {
                // Load departments with hierarchy information
                const departments = await this.orm.searchRead(
                    "account.analytic.account",
                    [["plan_id.code", "=", "departments"]],
                    ["id", "name", "code", "complete_name", "parent_id", "child_ids"],
                    {order: "code,name"}
                );

                // Build hierarchical structure
                this.state.departments = this._buildHierarchy(departments);
            }
        } catch (error) {
            console.error("Error loading departments:", error);
        } finally {
            this.state.loading = false;
        }
    }

    _processHierarchy(departments) {
        // Process pre-built hierarchy from backend
        const processNode = (node) => ({
            ...node,
            isSelected: this.props.selectedIds.includes(node.id),
            children: node.children ? node.children.map(processNode) : [],
        });

        return departments.map(processNode);
    }

    _buildHierarchy(departments) {
        const departmentMap = {};
        const roots = [];

        // First pass: create map
        departments.forEach((dept) => {
            departmentMap[dept.id] = {
                ...dept,
                children: [],
                level: 0,
                isSelected: this.props.selectedIds.includes(dept.id),
            };
        });

        // Second pass: build hierarchy
        departments.forEach((dept) => {
            if (dept.parent_id) {
                const parentId = dept.parent_id[0];
                if (departmentMap[parentId]) {
                    departmentMap[parentId].children.push(departmentMap[dept.id]);
                    departmentMap[dept.id].level = departmentMap[parentId].level + 1;
                }
            } else {
                roots.push(departmentMap[dept.id]);
            }
        });

        return roots;
    }

    toggleExpand(deptId) {
        if (this.state.expandedNodes.has(deptId)) {
            this.state.expandedNodes.delete(deptId);
        } else {
            this.state.expandedNodes.add(deptId);
        }
    }

    isExpanded(deptId) {
        return this.state.expandedNodes.has(deptId);
    }

    toggleDepartment(dept, event) {
        event.stopPropagation();

        const newSelectedIds = [...this.props.selectedIds];
        const deptIds = this._getDepartmentWithChildren(dept);

        if (dept.isSelected) {
            // Remove department and all children
            deptIds.forEach((id) => {
                const index = newSelectedIds.indexOf(id);
                if (index > -1) {
                    newSelectedIds.splice(index, 1);
                }
            });
        } else {
            // Add department and all children
            deptIds.forEach((id) => {
                if (!newSelectedIds.includes(id)) {
                    newSelectedIds.push(id);
                }
            });
        }

        this.props.onSelectionChange(newSelectedIds);
    }

    _getDepartmentWithChildren(dept) {
        const ids = [dept.id];
        if (dept.children) {
            dept.children.forEach((child) => {
                ids.push(...this._getDepartmentWithChildren(child));
            });
        }
        return ids;
    }

    onSearchInput(event) {
        this.state.searchTerm = event.target.value.toLowerCase();
    }

    _filterDepartments(departments, searchTerm) {
        if (!searchTerm) return departments;

        return departments
            .filter((dept) => {
                const matchesSelf =
                    dept.name.toLowerCase().includes(searchTerm) ||
                    (dept.code && dept.code.toLowerCase().includes(searchTerm));
                const matchesChildren =
                    dept.children &&
                    this._filterDepartments(dept.children, searchTerm).length > 0;
                return matchesSelf || matchesChildren;
            })
            .map((dept) => ({
                ...dept,
                children: this._filterDepartments(dept.children || [], searchTerm),
            }));
    }

    get filteredDepartments() {
        return this._filterDepartments(this.state.departments, this.state.searchTerm);
    }

    expandAll() {
        this._collectAllIds(this.state.departments).forEach((id) => {
            this.state.expandedNodes.add(id);
        });
    }

    collapseAll() {
        this.state.expandedNodes.clear();
    }

    _collectAllIds(departments) {
        const ids = [];
        departments.forEach((dept) => {
            ids.push(dept.id);
            if (dept.children) {
                ids.push(...this._collectAllIds(dept.children));
            }
        });
        return ids;
    }

    clearSelection() {
        this.props.onSelectionChange([]);
    }
}

DepartmentFilterSidebar.template = "budget.DepartmentFilterSidebar";
DepartmentFilterSidebar.props = {
    selectedIds: {type: Array},
    onSelectionChange: {type: Function},
    departments: {type: Array, optional: true},
    onClose: {type: Function, optional: true},
};

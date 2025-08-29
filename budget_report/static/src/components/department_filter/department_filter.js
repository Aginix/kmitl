/** @odoo-module */

import {Component, useState, onWillStart, onMounted, onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class DepartmentFilter extends Component {
    setup() {
        this.orm = useService("orm");
        
        this.state = useState({
            departments: [],
            expandedNodes: new Set(),
            searchTerm: "",
            loading: false,
            selectedIds: this.props.selectedIds || [],
        });

        this.resizeState = useState({
            isResizing: false,
            startX: 0,
            startWidth: 320,
            currentWidth: 320,
            minWidth: 250,
            maxWidth: 500,
        });

        onWillStart(async () => {
            await this.loadDepartments();
        });

        onMounted(() => {
            this.setupResizeHandlers();
        });

        onWillUnmount(() => {
            this.cleanupResizeHandlers();
        });
    }

    setupResizeHandlers() {
        this.onResizeMove = this.onResizeMove.bind(this);
        this.onResizeEnd = this.onResizeEnd.bind(this);
    }

    cleanupResizeHandlers() {
        document.removeEventListener('mousemove', this.onResizeMove);
        document.removeEventListener('mouseup', this.onResizeEnd);
    }

    async loadDepartments() {
        this.state.loading = true;
        try {
            if (this.props.departments && this.props.departments.length > 0) {
                this.state.departments = this._processHierarchy(this.props.departments);
            } else {
                const departments = await this.orm.searchRead(
                    "account.analytic.account",
                    [["root_plan_id.code", "=", "departments"]],
                    ["id", "name", "code", "complete_name", "parent_id", "child_ids"],
                    {order: "code,name"}
                );

                this.state.departments = this._buildHierarchy(departments);
            }
        } catch (error) {
            console.error("Error loading departments:", error);
        } finally {
            this.state.loading = false;
        }
    }

    _processHierarchy(departments) {
        const processNode = (node) => ({
            ...node,
            isSelected: this.state.selectedIds.includes(node.id),
            children: node.children ? node.children.map(processNode) : [],
        });

        return departments.map(processNode);
    }

    _buildHierarchy(departments) {
        const departmentMap = {};
        const roots = [];

        departments.forEach((dept) => {
            departmentMap[dept.id] = {
                ...dept,
                children: [],
                level: 0,
                isSelected: this.state.selectedIds.includes(dept.id),
            };
        });

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

    onResizeStart(event) {
        this.resizeState.isResizing = true;
        this.resizeState.startX = event.clientX;
        this.resizeState.startWidth = this.resizeState.currentWidth;
        
        document.addEventListener('mousemove', this.onResizeMove);
        document.addEventListener('mouseup', this.onResizeEnd);
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
        event.preventDefault();
    }

    onResizeMove(event) {
        if (!this.resizeState.isResizing) return;
        
        const deltaX = event.clientX - this.resizeState.startX;
        const newWidth = this.resizeState.startWidth + deltaX;
        
        if (newWidth >= this.resizeState.minWidth && newWidth <= this.resizeState.maxWidth) {
            this.resizeState.currentWidth = newWidth;
        }
    }

    onResizeEnd() {
        this.resizeState.isResizing = false;
        document.removeEventListener('mousemove', this.onResizeMove);
        document.removeEventListener('mouseup', this.onResizeEnd);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
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

    isSelected(deptId) {
        return this.state.selectedIds.includes(deptId);
    }

    toggleDepartment(dept, event) {
        event.stopPropagation();

        const newSelectedIds = [...this.state.selectedIds];
        const deptIds = this._getDepartmentWithChildren(dept);

        if (dept.isSelected) {
            deptIds.forEach((id) => {
                const index = newSelectedIds.indexOf(id);
                if (index > -1) {
                    newSelectedIds.splice(index, 1);
                }
            });
        } else {
            deptIds.forEach((id) => {
                if (!newSelectedIds.includes(id)) {
                    newSelectedIds.push(id);
                }
            });
        }

        this.state.selectedIds = newSelectedIds;
        this._updateSelectionState(this.state.departments, newSelectedIds);
        this.props.onSelectionChange(newSelectedIds);
    }

    _updateSelectionState(departments, selectedIds) {
        departments.forEach((dept) => {
            dept.isSelected = selectedIds.includes(dept.id);
            if (dept.children) {
                this._updateSelectionState(dept.children, selectedIds);
            }
        });
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
        this.state.selectedIds = [];
        this._updateSelectionState(this.state.departments, []);
        this.props.onSelectionChange([]);
    }
}

DepartmentFilter.template = "budget_report.DepartmentFilter";
DepartmentFilter.props = {
    onSelectionChange: {type: Function},
    selectedIds: {type: Array, optional: true},
    departments: {type: Array, optional: true},
};
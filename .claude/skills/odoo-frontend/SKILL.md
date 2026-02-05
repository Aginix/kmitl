---
name: odoo-frontend
description: Guide for Odoo Frontend skill. This skill covers Odoo 16 frontend development including OWL components, portal templates, and JavaScript patterns.
metadata:
  author: aginix
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Odoo Frontend Development Skill

## Overview
This skill covers Odoo 16 frontend development including OWL components, portal templates, and JavaScript patterns.

---

## OWL Framework (Odoo Web Library)

### Basic OWL Component Structure
```javascript
const { Component, useState, onMounted, onWillStart, mount, xml } = owl;

class MyComponent extends Component {
    static template = xml`
        <div class="my-component">
            <t t-if="state.loading">Loading...</t>
            <t t-else="">
                <t t-esc="state.data"/>
            </t>
        </div>
    `;

    setup() {
        this.state = useState({
            loading: true,
            data: null,
        });

        onMounted(() => {
            this._loadData();
        });
    }

    async _loadData() {
        // Load data via JSON-RPC
        this.state.loading = false;
    }
}
```

### OWL Template Syntax (QWeb)
```xml
<!-- Conditionals -->
<t t-if="condition">...</t>
<t t-elif="condition2">...</t>
<t t-else="">...</t>

<!-- Loops -->
<t t-foreach="items" t-as="item" t-key="item.id">
    <div><t t-esc="item.name"/></div>
    <div><t t-esc="item_index"/></div> <!-- 0-based index -->
</t>

<!-- Attributes -->
<div t-att-class="dynamicClass"/>
<div t-att-data-id="item.id"/>
<option t-att-selected="isSelected(item.id)"/>

<!-- Events -->
<button t-on-click="onClick">Click</button>
<select t-on-change="onChange">...</select>

<!-- Raw HTML (careful with XSS) -->
<div t-out="htmlContent"/>
```

### Important OWL Template Limitations
- **No inline JavaScript functions**: Cannot use `String()`, `parseInt()`, etc. directly in templates
- **Solution**: Create helper methods in the component class

```javascript
// BAD - Will cause "ctx.String is not a function" error
static template = xml`
    <option t-att-selected="String(fy.id) === String(state.fiscalYearId)">
`;

// GOOD - Use helper method
static template = xml`
    <option t-att-selected="isFiscalYearSelected(fy.id)">
`;

isFiscalYearSelected(fyId) {
    return String(fyId) === String(this.state.fiscalYearId);
}
```

### Manual OWL Component Mounting (Portal)
```javascript
function mountMyComponent() {
    const container = document.getElementById('my_component_mount');
    if (!container) return;

    // Parse data attributes from server
    const data = JSON.parse(container.dataset.myData || '[]');

    mount(MyComponent, container, {
        props: {
            data,
            initialValue: container.dataset.initialValue || null,
        },
    });
}

// Auto-mount when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountMyComponent);
} else {
    mountMyComponent();
}
```

---

## Portal Templates

### Basic Portal Layout
```xml
<template id="my_portal_page" name="My Portal Page">
    <t t-call="portal.portal_layout">
        <!-- Disable breadcrumbs -->
        <t t-set="no_breadcrumbs" t-value="1"/>

        <!-- Your content -->
        <div id="my_component_mount"
             t-att-data-my-data="my_data_json"
             t-att-data-initial-value="initial_value">
        </div>
    </t>
</template>
```

### Portal Layout Options
```xml
<!-- Available t-set variables -->
<t t-set="no_breadcrumbs" t-value="1"/>  <!-- Hide breadcrumbs -->
<t t-set="no_header" t-value="1"/>        <!-- Hide header -->
<t t-set="o_portal_fullwidth_alert"/>     <!-- Full-width alerts -->
```

### Controller for Portal
```python
from odoo import http
from odoo.http import request
import json

class MyPortalController(http.Controller):

    @http.route("/my/page", type="http", auth="public", website=True)
    def my_page(self, **kw):
        values = self._prepare_values(**kw)
        return request.render("my_module.my_portal_page", values)

    @http.route("/my/page/api", type="json", auth="public", csrf=False)
    def my_page_api(self, **kw):
        # Return JSON data for OWL component
        return {"data": [...]}

    def _prepare_values(self, **kw):
        # Prepare data for template
        data = [...]
        return {
            "my_data_json": json.dumps(data),
            "initial_value": kw.get("value", ""),
        }
```

---

## JSON-RPC API Calls

### From OWL Component
```javascript
async _callApi(endpoint, params = {}) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: Date.now(),
        }),
    });

    const result = await response.json();

    if (result.error) {
        throw new Error(result.error.message || 'API Error');
    }

    return result.result;
}

// Usage
const data = await this._callApi('/my/page/api', {
    fiscal_year_id: this.state.fiscalYearId,
    department_id: this.state.departmentId,
});
```

---

## Assets Registration

### In __manifest__.py
```python
"assets": {
    # Backend (Odoo UI)
    "web.assets_backend": [
        "my_module/static/src/components/**/*",
    ],
    # Frontend (Portal/Website)
    "web.assets_frontend": [
        "my_module/static/src/portal/scss/styles.scss",
        "my_module/static/src/portal/js/components.js",
    ],
},
```

---

## SCSS Styling

### Portal Container Override
```scss
// Make portal container full-width
.o_portal {
    > .container {
        max-width: 100%;
        width: 100%;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }
}
```

### Component Styling
```scss
#my_component {
    .card {
        border: none;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .form-select:focus {
        border-color: #e67e22;
        box-shadow: 0 0 0 0.2rem rgba(230, 126, 34, 0.15);
    }
}

// Responsive
@media (max-width: 768px) {
    #my_component {
        .col {
            flex: 0 0 100%;
            max-width: 100%;
        }
    }
}
```

---

## URL State Management

### Sync Filters with URL
```javascript
_initFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const urlValue = params.get('my_param');

    if (urlValue) {
        this.state.myParam = urlValue;
    }

    this._updateUrl(false); // replaceState, don't pushState
}

_updateUrl(pushState = true) {
    const params = new URLSearchParams();
    if (this.state.myParam) {
        params.set('my_param', this.state.myParam);
    }

    const newUrl = `/my/page?${params.toString()}`;
    if (pushState) {
        history.pushState(null, '', newUrl);
    } else {
        history.replaceState(null, '', newUrl);
    }
}

onFilterChange(ev) {
    this.state.myParam = ev.target.value || null;
    this._updateUrl();
    this._loadData();
}
```

---

## Common Patterns

### Number Formatting
```javascript
formatNumber(num) {
    if (num === null || num === undefined || num === 0) {
        return '-';
    }
    return num.toLocaleString('th-TH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
```

### State Badge Classes
```javascript
getStateClass(state) {
    const classes = {
        'draft': 'badge bg-secondary',
        'review': 'badge bg-warning',
        'approved': 'badge bg-success',
        'cancel': 'badge bg-danger',
    };
    return classes[state] || 'badge bg-secondary';
}
```

### Loading States in Template
```xml
<t t-if="state.loading">
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
</t>
<t t-elif="state.error">
    <div class="text-danger">Error loading data</div>
</t>
<t t-elif="!state.items.length">
    <div class="text-muted">No data</div>
</t>
<t t-else="">
    <!-- Render items -->
</t>
```

---

## File Structure
```
my_module/
├── __manifest__.py
├── controller/
│   ├── __init__.py
│   └── portal.py
├── views/
│   └── portal_templates.xml
└── static/
    └── src/
        └── portal/
            ├── js/
            │   └── components.js
            └── scss/
                └── styles.scss
```

---

## Dashboard Development with ECharts

### ECharts Integration in OWL Component

#### Loading ECharts Library
```javascript
async _loadECharts() {
    if (typeof echarts !== "undefined") {
        return;
    }
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}
```

#### Chart Instance Management
```javascript
setup() {
    // Initialize chart instances as null
    this.pieChart = null;
    this.barChart = null;
    this.sankeyChart = null;

    onWillStart(async () => {
        await this._loadECharts();
        await this.loadData();
    });

    onMounted(() => {
        this._initCharts();
    });

    onWillUnmount(() => {
        this._disposeCharts();
    });
}

_disposeCharts() {
    if (this.pieChart) {
        this.pieChart.dispose();
        this.pieChart = null;
    }
    if (this.barChart) {
        this.barChart.dispose();
        this.barChart = null;
    }
    // ... dispose other charts
}
```

#### Tab-Based Chart Initialization
```javascript
_initCharts() {
    // Delay to ensure DOM is ready
    setTimeout(() => {
        const activeTab = this.state.activeTab;
        if (activeTab === "overview") {
            this._updatePieChart();
        } else if (activeTab === "department") {
            this._updateTreeMap();
        } else if (activeTab === "executive") {
            this._updateFundPieChart();
            this._updateStackedBarChart();
            this._updateSankeyChart();
        }
    }, 100);
}

onTabChange(tabId) {
    this.state.activeTab = tabId;
    // Re-initialize charts after tab change
    setTimeout(() => {
        this._initCharts();
    }, 100);
}
```

### ECharts Chart Types

#### Pie Chart
```javascript
_updatePieChart() {
    if (typeof echarts === "undefined") return;

    const chartDom = document.getElementById("myPieChart");
    if (!chartDom) return;

    if (!this.pieChart) {
        this.pieChart = echarts.init(chartDom);
        window.addEventListener("resize", () => {
            if (this.pieChart) this.pieChart.resize();
        });
    }

    const data = this.state.stats.pie_data || [];

    const option = {
        tooltip: {
            trigger: "item",
            formatter: (params) => {
                const value = this.formatCurrency(params.value);
                return `${params.name}: ${value} บาท (${params.percent.toFixed(1)}%)`;
            },
        },
        title: {
            text: "งบประมาณตามกองทุน",
            left: "center",
            top: 0,
            textStyle: { fontSize: 18, fontWeight: "bold", color: "#3c3c41" },
        },
        legend: {
            orient: 'vertical',
            right: 0,
            top: 'center',
        },
        series: [{
            name: "กองทุน",
            type: "pie",
            radius: '60%',
            center: ['30%', '50%'],
            label: {
                show: true,
                formatter: (params) => params.percent < 5 ? "" : `${params.percent.toFixed(0)}%`,
                position: "inside",
                fontSize: 10,
                fontWeight: "bold",
                color: "#fff",
            },
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowOffsetX: 0,
                    shadowColor: "rgba(0, 0, 0, 0.2)",
                },
            },
            data: data,
        }],
    };

    this.pieChart.setOption(option, true);
}
```

#### TreeMap Chart
```javascript
_updateTreeMap() {
    const chartDom = document.getElementById("budgetTreeMap");
    if (!chartDom) return;

    if (!this.treeMapChart) {
        this.treeMapChart = echarts.init(chartDom);
        window.addEventListener("resize", () => {
            if (this.treeMapChart) this.treeMapChart.resize();
        });
    }

    const data = this.state.stats.treemap_data || [];

    const option = {
        tooltip: {
            formatter: (params) => {
                const value = this.formatCurrency(params.value);
                return `${params.name}<br/>งบประมาณ: ${value} บาท`;
            },
        },
        series: [{
            type: "treemap",
            data: data,
            leafDepth: 2,
            roam: false,
            nodeClick: "zoomToNode",
            breadcrumb: {
                show: true,
                top: 5,
            },
            label: {
                show: true,
                formatter: "{b}",
                fontSize: 12,
            },
            upperLabel: {
                show: true,
                height: 30,
                formatter: (params) => {
                    const value = this.formatCurrency(params.value);
                    return `${params.name} (${value})`;
                },
            },
            levels: [
                { itemStyle: { borderColor: "#777", borderWidth: 2, gapWidth: 2 } },
                { itemStyle: { borderColor: "#999", borderWidth: 1, gapWidth: 1 }, upperLabel: { show: true } },
                { itemStyle: { borderColor: "#bbb", borderWidth: 1, gapWidth: 1 } },
            ],
        }],
    };

    this.treeMapChart.setOption(option, true);
}
```

#### Sankey Chart
```javascript
_updateSankeyChart() {
    const chartDom = document.getElementById("sankeyChart");
    if (!chartDom) return;

    if (!this.sankeyChart) {
        this.sankeyChart = echarts.init(chartDom);
        window.addEventListener("resize", () => {
            if (this.sankeyChart) this.sankeyChart.resize();
        });
    }

    const sankeyData = this.state.stats.sankey_data || { nodes: [], links: [] };

    const option = {
        title: {
            text: "การไหลของงบประมาณ: กองทุน → หน่วยงาน → ประเภทงบ",
            left: "center",
            top: 0,
        },
        tooltip: {
            trigger: "item",
            triggerOn: "mousemove",
            formatter: (params) => {
                if (params.dataType === "edge") {
                    const value = this.formatCurrency(params.value);
                    return `${params.data.source} → ${params.data.target}<br/>งบประมาณ: ${value} บาท`;
                }
                return params.name;
            },
        },
        series: [{
            type: "sankey",
            layout: "none",
            emphasis: { focus: "adjacency" },
            nodeAlign: "left",
            orient: "horizontal",
            draggable: true,
            top: 50,
            left: 20,
            right: 150,
            bottom: 20,
            nodeWidth: 20,
            nodeGap: 10,
            data: sankeyData.nodes,
            links: sankeyData.links,
            label: {
                position: "right",
                fontSize: 11,
            },
            lineStyle: {
                color: "gradient",
                curveness: 0.5,
            },
        }],
    };

    this.sankeyChart.setOption(option, true);
}
```

#### Stacked Bar Chart (Horizontal, Percentages)
```javascript
_updateStackedBarChart() {
    const chartDom = document.getElementById("stackedBarChart");
    if (!chartDom) return;

    if (!this.stackedBarChart) {
        this.stackedBarChart = echarts.init(chartDom);
        window.addEventListener("resize", () => {
            if (this.stackedBarChart) this.stackedBarChart.resize();
        });
    }

    const barData = this.state.stats.stacked_bar_data || { departments: [], account_types: [], series: [] };

    const option = {
        title: {
            text: "สัดส่วนประเภทงบตามหน่วยงาน (%)",
            left: "center",
            top: 0,
            textStyle: { fontSize: 16 },
        },
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            formatter: (params) => {
                let result = `<strong>${params[0].axisValue}</strong><br/>`;
                params.forEach(p => {
                    if (p.value > 0) {
                        result += `${p.marker} ${p.seriesName}: ${p.value.toFixed(1)}%<br/>`;
                    }
                });
                return result;
            },
        },
        legend: {
            top: 30,
            left: "center",
            type: "scroll",
        },
        grid: {
            left: "3%",
            right: "4%",
            bottom: "3%",
            top: 80,
            containLabel: true,
        },
        xAxis: {
            type: "value",
            max: 100,
            axisLabel: { formatter: "{value}%" },
        },
        yAxis: {
            type: "category",
            data: barData.departments,
            axisLabel: { fontSize: 11 },
        },
        series: barData.series.map(s => ({
            name: s.name,
            type: "bar",
            stack: "total",
            emphasis: { focus: "series" },
            label: {
                show: true,
                formatter: (params) => params.value > 5 ? `${params.value.toFixed(0)}%` : "",
                fontSize: 10,
            },
            data: s.data,
        })),
    };

    this.stackedBarChart.setOption(option, true);
}
```

### Backend Data Building Patterns

#### Hierarchical Data Aggregation (Leaf to Root)
```python
def _build_activity_table(self, expense_lines):
    """Build table with hierarchical activity data.

    Data is collected from deepest level and summed up to ancestors.
    """
    # Step 1: Collect leaf data and all ancestors
    leaf_data = {}  # {(activity_id, column_id): amount}
    all_activities = {}  # {id: activity record}
    columns = {}  # {id: name}

    for line in expense_lines:
        activity = line.activity_analytic_id
        if not activity:
            continue

        amount = line.balance or 0

        # Collect activity and all ancestors
        current = activity
        while current:
            if current.id not in all_activities:
                all_activities[current.id] = current
            current = current.parent_id

        # Store leaf amount
        key = (activity.id, column_id)
        leaf_data[key] = leaf_data.get(key, 0) + amount

    # Step 2: Aggregate from leaves up to all ancestors
    aggregated = {}
    for (act_id, col_id), amount in leaf_data.items():
        current = all_activities[act_id]
        while current:
            key = (current.id, col_id)
            aggregated[key] = aggregated.get(key, 0) + amount
            current = current.parent_id

    # Step 3: Determine level for each activity
    activity_levels = {}
    for act_id, activity in all_activities.items():
        level = 0
        current = activity
        while current.parent_id:
            level += 1
            current = current.parent_id
        activity_levels[act_id] = level

    # Step 4: Build rows with recursive children
    rows = []
    # ... build hierarchical rows
    return {"columns": columns, "rows": rows}
```

#### Root Level Extraction Pattern
```python
def _get_root(self, record):
    """Get root level of hierarchical record."""
    root = record
    while root.parent_id:
        root = root.parent_id
    return root

# Usage in data building
for line in expense_lines:
    dept = line.department_analytic_id
    if not dept:
        continue

    # Get root department
    root_dept = self._get_root(dept)
    key = root_dept.id
    # ... aggregate data
```

### Dashboard XML Template Patterns

#### Tab Navigation
```xml
<ul class="nav nav-tabs mb-4">
    <li class="nav-item">
        <a t-attf-class="nav-link #{isTabActive('overview') ? 'active' : ''}"
           href="#"
           t-on-click.prevent="() => this.onTabChange('overview')">
            ภาพรวม
        </a>
    </li>
    <!-- Dropdown Tab -->
    <li class="nav-item dropdown">
        <a t-attf-class="nav-link dropdown-toggle #{state.activeTab.startsWith('expense') ? 'active' : ''}"
           href="#"
           data-bs-toggle="dropdown">
            <span class="text-danger">รายจ่าย</span>
        </a>
        <ul class="dropdown-menu">
            <li>
                <a t-attf-class="dropdown-item #{isTabActive('expense-dept') ? 'active' : ''}"
                   href="#"
                   t-on-click.prevent="() => this.onTabChange('expense-dept')">
                    ตามหน่วยงาน
                </a>
            </li>
        </ul>
    </li>
</ul>
```

#### Dynamic Table with Hierarchical Rows
```xml
<table class="table table-sm table-bordered table-hover mb-0" style="font-size: 11px;">
    <thead class="table-light sticky-top">
        <tr>
            <th class="text-nowrap">กิจกรรม</th>
            <t t-foreach="state.stats.table?.columns || []" t-as="col" t-key="col.id">
                <th class="text-end text-nowrap" t-esc="col.name"/>
            </t>
            <th class="text-end text-nowrap">รวม</th>
        </tr>
    </thead>
    <tbody>
        <t t-foreach="state.stats.table?.rows || []" t-as="row" t-key="row.id">
            <tr t-attf-class="#{row.level === 0 ? 'fw-bold table-secondary' : ''}">
                <!-- Indentation based on level -->
                <td t-attf-style="padding-left: #{row.level * 16 + 4}px;">
                    <t t-esc="row.name"/>
                </td>
                <t t-foreach="state.stats.table?.columns || []" t-as="col" t-key="col.id">
                    <td class="text-end">
                        <t t-if="row.data[col.id]" t-esc="formatCurrency(row.data[col.id])"/>
                        <t t-else="">-</t>
                    </td>
                </t>
                <td class="text-end fw-bold" t-esc="formatCurrency(row.total)"/>
            </tr>
        </t>
    </tbody>
</table>
```

#### Executive Dashboard Layout (Print-Ready)
```xml
<!-- Row 1: Summary + Pie Charts -->
<div class="row g-3 mb-3 align-items-center">
    <!-- Total Card (compact) -->
    <div class="col-auto">
        <div class="card border-0 shadow-sm border-start border-danger border-4">
            <div class="card-body text-center py-3 px-4">
                <div class="text-muted mb-1">ประมาณการรายจ่ายรวม</div>
                <div class="h2 fw-semibold text-danger mb-0">
                    <t t-esc="formatCurrency(state.stats.total_expense)"/>
                </div>
                <div class="text-muted small">บาท</div>
            </div>
        </div>
    </div>
    <!-- Pie Chart -->
    <div class="col-lg-4">
        <div class="card border-0 shadow-sm h-100">
            <div class="card-body py-2">
                <div id="fundPieChart" style="height: 300px;"></div>
            </div>
        </div>
    </div>
</div>

<!-- Row 2: Charts Side by Side -->
<div class="row g-3 mb-3">
    <div class="col-lg-6">
        <div class="card border-0 shadow-sm">
            <div class="card-body py-2">
                <div id="departmentPieChart" style="height: 412px;"></div>
            </div>
        </div>
    </div>
    <div class="col-lg-6">
        <div class="card border-0 shadow-sm">
            <div class="card-body py-2">
                <div id="stackedBarChart" style="height: 412px;"></div>
            </div>
        </div>
    </div>
</div>
```

### Dashboard File Structure
```
my_report_module/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   └── main.py              # Data building methods
├── views/
│   └── dashboard_views.xml   # Menu and action
└── static/
    └── src/
        └── components/
            └── dashboard/
                ├── dashboard.js    # OWL Component
                ├── dashboard.xml   # QWeb Template
                └── dashboard.scss  # Styles (optional)
```

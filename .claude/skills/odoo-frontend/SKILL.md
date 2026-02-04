---
name: odoo-frontend
description: Guide for Odoo Frontend skill. This skill covers Odoo 16 frontend development including OWL components, portal templates, and JavaScript patterns.
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

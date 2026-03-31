/** @odoo-module **/

/**
 * Extract the integer ID from a Many2one field value in record.data.
 * Handles both [id, name] tuples and {id, display_name} objects.
 */
export function getMany2oneId(recordData, fieldName) {
    const val = recordData[fieldName];
    if (!val) return false;
    return val[0] || val.id || false;
}

/**
 * Extract the display name from a Many2one field value in record.data.
 */
export function getMany2oneDisplay(recordData, fieldName) {
    const val = recordData[fieldName];
    if (!val) return "";
    return val[1] || val.display_name || "";
}

/**
 * Format a number as Thai Baht currency string.
 */
export function formatThaiCurrency(amount) {
    return Number(amount || 0).toLocaleString("th-TH", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

/** Budget dimension field names used across widgets. */
export const BUDGET_DIMENSION_FIELDS = [
    "budget_account_id",
    "activity_analytic_id",
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
];

/**
 * Build analytic data dict from record data for RPC calls.
 * Keys are mapped to the backend's expected format.
 */
export function buildAnalyticData(recordData) {
    return {
        account_id: getMany2oneId(recordData, "budget_account_id"),
        activity_analytic_id: getMany2oneId(recordData, "activity_analytic_id"),
        department_analytic_id: getMany2oneId(recordData, "department_analytic_id"),
        fund_analytic_id: getMany2oneId(recordData, "fund_analytic_id"),
        source_analytic_id: getMany2oneId(recordData, "source_analytic_id"),
    };
}

/**
 * Check if all budget dimension fields have values.
 */
export function allDimensionsFilled(analyticData) {
    return (
        analyticData.account_id &&
        analyticData.activity_analytic_id &&
        analyticData.department_analytic_id &&
        analyticData.fund_analytic_id &&
        analyticData.source_analytic_id
    );
}

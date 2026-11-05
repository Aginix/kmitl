/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";

/**
 * Tax totals widget for purchase requests: the pencil before the VAT label
 * opens a wizard to override the computed VAT.
 */
export class PurchaseRequestTaxTotals extends TaxTotalsComponent {
    get canEditVat() {
        const data = this.props.record.data;
        return Boolean(data.is_vat_editable && data.tax_id);
    }

    openVatWizard() {
        this.env.onClickViewButton({
            clickParams: { type: "object", name: "action_open_vat_wizard" },
            getResParams: () => {
                const record = this.props.record;
                return {
                    context: record.context,
                    evalContext: record.evalContext,
                    resModel: record.resModel,
                    resId: record.resId,
                    resIds: [record.resId],
                };
            },
        });
    }
}
PurchaseRequestTaxTotals.template = "purchase_request_vat_manual.TaxTotalsField";

registry.category("fields").add("pr_vat_tax_totals", PurchaseRequestTaxTotals);

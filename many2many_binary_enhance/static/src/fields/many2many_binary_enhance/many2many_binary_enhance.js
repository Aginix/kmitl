/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { useService } from "@web/core/utils/hooks";

patch(Many2ManyBinaryField.prototype, 'many2many_binary_enhance', {
    setup() {
        this._super(...arguments);
        this.action = useService("action");
    },
    
    async onEditAttachment(fileId) {
        const action = {
            type: 'ir.actions.act_window',
            res_model: 'attachment.name.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_attachment_id: fileId,
                active_model: this.props.record.resModel,
                active_id: this.props.record.resId,
            },
        };
        
        const result = await this.action.doAction(action, {
            onClose: async () => {
                await this.props.record.load();
                await this.props.record.model.notify();
            },
        });
    }
});
/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

// Full-screen landing page for un-provisioned internal users. Reached only as
// the user's home action (see ir.http.session_info), never via a menu.
export class ProvisioningNotice extends Component {
    setup() {
        this.orm = useService("orm");
        this.company = useService("company");
        this.state = useState({
            company: {name: "", email: "", phone: ""},
        });

        onWillStart(async () => {
            const companyId = this.company.currentCompany.id;
            const [record] = await this.orm.read(
                "res.company",
                [companyId],
                ["name", "email", "phone"]
            );
            this.state.company = {
                name: record.name || "",
                email: record.email || "",
                phone: record.phone || "",
            };
        });
    }

    logout() {
        window.location = "/web/session/logout";
    }
}

ProvisioningNotice.template = "kmitl_user_provisioning.ProvisioningNotice";
registry.category("actions").add("kmitl_provisioning_notice", ProvisioningNotice);

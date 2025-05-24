/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from '@web/core/l10n/translation';

const { Component, onWillStart } = owl;

class AlanConfigDialog extends Dialog {}
AlanConfigDialog.props = {
    ...Dialog.props,
    size: { type: String, optional: true, validate: (s) => ["sm", "md", "lg", "xl" ,"as-full-screen"].includes(s) },
};
AlanConfigDialog.defaultProps = {
    ...Dialog.defaultProps,
    title: _t("Alan Feature Settings")
};

class AlanConfiguration extends Component {
    setup(){
        this.rpc = useService("rpc");
        onWillStart(this._fetch_configuration);
    }

    async _fetch_configuration(){
        this.configuration = await this.rpc('/get_alan_configuration');
    }
    async _setting_change(ev){
        let is_active = $(ev.target).prop("checked");
        let setting = $(ev.target).attr("id");
        await this.rpc('/set_alan_configuration',
                    {'is_active':is_active, 'setting': setting});
    }
}

AlanConfiguration.template = "theme_alan.alan_configuration"
AlanConfiguration.components = { AlanConfigDialog }

class AlanTouch extends Component {
    setup() {
        this.dialogs = useService('dialog');
    }
    show_configuration(){
        this.dialogs.add(AlanConfiguration, {});
    }
}

AlanTouch.template = "theme_alan.alan_touch";

export const systrayItem = {
    Component: AlanTouch,
};

registry.category("website_systray").add("alanTouch", systrayItem, { sequence: 15 });

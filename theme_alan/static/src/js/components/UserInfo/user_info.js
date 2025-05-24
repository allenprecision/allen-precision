/** @odoo-module alias=theme_alan.UserInformDialog **/

import { Dialog } from "@web/core/dialog/dialog";
const { Component } = owl;

class UserInformDialog extends Component {
    setup() {
        this.title = "Test";
        this.footer = false;
        this.header = false;
    }
    _confirm(){
        this.props.onConfirm();
        this.props.close();
    }
    _cancel(){
        this.props.close();
    }
}
UserInformDialog.components = { Dialog };
UserInformDialog.template = 'theme_alan.userInformDialog';


export default {
    UserInformDialog: UserInformDialog,
}

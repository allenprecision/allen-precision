/** @odoo-module  alias=theme_alan.Menu **/

import { MenuDialog, EditMenuDialog } from '@website/components/dialog/edit_menu';
import { patch } from "@web/core/utils/patch";

const {useState, useEffect } = owl;

const useControlledInput = (initialValue, validate) => {
    const input = useState({
        value: initialValue,
        hasError: false,
    });

    const isValid = () => {
        if (validate(input.value)) {
            return true;
        }
        input.hasError = true;
        return false;
    };

    useEffect(() => {
        input.hasError = false;
    }, () => [input.value]);

    return {
        input,
        isValid,
    };
};

patch(MenuDialog.prototype, {
    setup() {
        super.setup();
        this.is_tag_active = useControlledInput(this.props.is_tag_active, value => !!value);
        this.tag_text = useControlledInput(this.props.tag_text, value => !!value);
        this.tag_text_color = useControlledInput(this.props.tag_text_color, value => !!value);
        this.tag_bg_color = useControlledInput(this.props.tag_bg_color, value => !!value);
        this.hlt_menu = useControlledInput(this.props.hlt_menu, value=> !!value);
        this.hlt_menu_bg_color = useControlledInput(this.props.hlt_menu_bg_color, value => !!value);
        this.hlt_menu_ft_col = useControlledInput(this.props.hlt_menu_ft_col, value => !!value);
        this.hlt_menu_icon = useControlledInput(this.props.hlt_menu_icon, value => !!value);
    },

    onClickOk() {
        if (this.name.isValid()) {
            if (this.props.isMegaMenu || this.url.isValid()) {
                this.props.save(this.name.input.value, this.url.input.value,
                    this.tag_text.input.value,
                    this.is_tag_active.input.value,
                    this.tag_bg_color.input.value,
                    this.tag_text_color.input.value,
                    this.hlt_menu.input.value,
                    this.hlt_menu_bg_color.input.value,
                    this.hlt_menu_ft_col.input.value,
                    this.hlt_menu_icon.input.value,
                );
                this.props.close();
            }
        }
    }

})

MenuDialog.template = 'theme_alan.MenuDialog';
MenuDialog.props = {
    ...MenuDialog.props,
    is_tag_active: { type: Boolean, optional: true },
    tag_text: {optional: true  },
    tag_bg_color: { optional: true },
    tag_text_color:{optional: true },
    hlt_menu: { type: Boolean,optional: true },
    hlt_menu_bg_color: {optional: true  },
    hlt_menu_ft_col:{optional: true },
    hlt_menu_icon: { optional: true },
};

patch(EditMenuDialog.prototype, {
    addMenu(isMegaMenu) {
        this.dialogs.add(MenuDialog, {
            isMegaMenu,
            save: (name, url, isNewWindow, tag_text,is_tag_active,tag_text_color,tag_bg_color,
                hlt_menu,hlt_menu_bg_color,hlt_menu_ft_col,hlt_menu_icon) => {
                const newMenu = {
                    fields: {
                        id: `menu_${(new Date).toISOString()}`,
                        name,
                        url: isMegaMenu ? '#' : url,
                        new_window: isNewWindow,
                        'is_mega_menu': isMegaMenu,
                        sequence: 0,
                        'parent_id': false,
                        'tag_text': tag_text,
                        'is_tag_active' : is_tag_active,
                        'tag_bg_color':tag_bg_color,
                        'tag_text_color':tag_text_color,
                        'hlt_menu': hlt_menu,
                        'hlt_menu_bg_color' : hlt_menu_bg_color,
                        'hlt_menu_ft_col':hlt_menu_ft_col,
                        'hlt_menu_icon':hlt_menu_icon,
                    },
                    'children': [],
                };
                this.map.set(newMenu.fields['id'], newMenu);
                this.state.rootMenu.children.push(newMenu);
            },
        });
    },

    editMenu(id) {
        const menuToEdit = this.map.get(id);
        this.dialogs.add(MenuDialog, {
            name: menuToEdit.fields['name'],
            url: menuToEdit.fields['url'],
            isMegaMenu: menuToEdit.fields['is_mega_menu'],
            tag_text: menuToEdit.fields['tag_text'],
            is_tag_active: menuToEdit.fields['is_tag_active'],
            tag_bg_color: menuToEdit.fields['tag_bg_color'],
            tag_text_color: menuToEdit.fields['tag_text_color'],
            hlt_menu: menuToEdit.fields['hlt_menu'],
            hlt_menu_bg_color: menuToEdit.fields['hlt_menu_bg_color'],
            hlt_menu_ft_col: menuToEdit.fields['hlt_menu_ft_col'],
            hlt_menu_icon: menuToEdit.fields['hlt_menu_icon'],
            save: (name, url,tag_text,is_tag_active,tag_bg_color,tag_text_color,
                hlt_menu,hlt_menu_bg_color,hlt_menu_ft_col,hlt_menu_icon) => {
                menuToEdit.fields['name'] = name;
                menuToEdit.fields['url'] = url;
                menuToEdit.fields['tag_text'] = tag_text;
                menuToEdit.fields['is_tag_active'] = is_tag_active;
                menuToEdit.fields['tag_bg_color'] = tag_bg_color;
                menuToEdit.fields['tag_text_color'] = tag_text_color;
                menuToEdit.fields['hlt_menu'] = hlt_menu;
                menuToEdit.fields['hlt_menu_bg_color'] = hlt_menu_bg_color;
                menuToEdit.fields['hlt_menu_ft_col'] = hlt_menu_ft_col;
                menuToEdit.fields['hlt_menu_icon'] = hlt_menu_icon;
                this.state.rootMenu.children = [...this.state.rootMenu.children];
            },
        });
    }
})
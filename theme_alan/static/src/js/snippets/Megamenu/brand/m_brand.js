/** @odoo-module alias=theme_alan.MegaMenuBrand **/

import { SelectData } from "theme_alan.SelectData";

const { Component, useSubEnv } = owl;

class MegaMenuBrand extends Component {
    setup(){
        /** Setup Method  */
        // Required to go back
        useSubEnv({'SnippetPicker':this.env.SnippetPicker})

        // Frame Columne Size
        this.props.col_size = this.env.SnippetBox.props.col_size;
        // Select Config Identifier
        this.props.selete_data_config = "MegaMenuBrand"
        // Search
        this.props.search = "as.product.brand";
        // Quick Search Option
        this.props.quick_search = []

        // Slider Styles
        this.props.slider_styles = [['Slider Style 1','theme_alan.m_brand_slider', 'as-mm-brand-snippet-1'],
        ['Slider Style 2','theme_alan.m_brand_slider', 'as-mm-brand-snippet-2'],
        ['Slider Style 3','theme_alan.m_brand_slider', 'as-mm-brand-snippet-3'],
        ['Slider Style 4','theme_alan.m_brand_slider', 'as-mm-brand-snippet-4'],
        ['Slider Style 5','theme_alan.m_brand_slider', 'as-mm-brand-snippet-5']]

        // Grid Styles
        this.props.grid_styles = [['Grid Style 1','theme_alan.m_brand_grid', 'as-mm-brand-snippet-1'],
        ['Grid Style 2','theme_alan.m_brand_grid', 'as-mm-brand-snippet-2'],
        ['Grid Style 3','theme_alan.m_brand_grid', 'as-mm-brand-snippet-3'],
        ['Grid Style 4','theme_alan.m_brand_grid', 'as-mm-brand-snippet-4'],
        ['Grid Style 5','theme_alan.m_brand_grid', 'as-mm-brand-snippet-5']]

        // Design and Edit option
        if(this.env.SnippetBox.props.initData != undefined){
            this.props.design_and_edit = this.env.SnippetBox.props.initData.design_edit;
            this.props.init_record_ids = this.env.SnippetBox.props.initData.record_ids;
        }else{
            this.props.design_and_edit = {
                'snippet':'MegaMenuBrand',
                'frame_col':this.props.col_size,
                'active_view':'slider',
                'auto_slider':true,
                'slider_time':4,
                'default_stemplate_id':'theme_alan.m_brand_slider',
                'default_gtemplate_id':'theme_alan.m_brand_grid',
                'template_id':'theme_alan.m_brand_slider',
                'slider_style':'as-mm-brand-snippet-1',
                'grid_style':'as-mm-brand-snippet-1',
                'col_item':4,
                'slider':true,
                'grid':true,
                'allow_link':true,
            }
        }

        useSubEnv({"MegaMenuBrand":this})
    }
}

MegaMenuBrand.template = 'theme_alan.m_brand_configuration';
MegaMenuBrand.components = { SelectData };

export default {
    MegaMenuBrand: MegaMenuBrand,
}
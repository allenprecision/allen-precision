/** @odoo-module alias=theme_alan.MegaMenuProduct **/

import { SelectData } from "theme_alan.SelectData";

const { Component, useSubEnv } = owl;

class MegaMenuProduct extends Component {
    setup(){
        /** Setup Method  */
        // Required to go back
        useSubEnv({'SnippetPicker':this.env.SnippetPicker})

        // Frame Columne Size
        this.props.col_size = this.env.SnippetBox.props.col_size;
        // Select Config Identifier
        this.props.selete_data_config = "MegaMenuProduct"
        // Search
        this.props.search = "product.template";
        // Quick Search Option
        this.props.quick_search = ['newest','top_rated','best_seller']

        // Slider Styles
        this.props.slider_styles = [['Slider Style 1','theme_alan.m_product_slider', 'as-mm-product-snippet-1'],
        ['Slider Style 2','theme_alan.m_product_slider', 'as-mm-product-snippet-2'],
        ['Slider Style 3','theme_alan.m_product_slider', 'as-mm-product-snippet-3'],
        ['Slider Style 4','theme_alan.m_product_slider', 'as-mm-product-snippet-4'],
        ['Slider Style 5','theme_alan.m_product_slider', 'as-mm-product-snippet-5']]

        // Grid Styles
        this.props.grid_styles = [['Slider Style 1','theme_alan.m_product_grid', 'as-mm-product-snippet-1'],
        ['Slider Style 2','theme_alan.m_product_grid', 'as-mm-product-snippet-2'],
        ['Slider Style 3','theme_alan.m_product_grid', 'as-mm-product-snippet-3'],
        ['Slider Style 4','theme_alan.m_product_grid', 'as-mm-product-snippet-4'],
        ['Slider Style 5','theme_alan.m_product_grid', 'as-mm-product-snippet-5']]

        // Design and Edit option
        if(this.env.SnippetBox.props.initData != undefined){
            this.props.design_and_edit = this.env.SnippetBox.props.initData.design_edit;
            this.props.init_record_ids = this.env.SnippetBox.props.initData.record_ids;
        }else{
            this.props.design_and_edit = {
                'snippet':'MegaMenuProduct',
                'frame_col':this.props.col_size,
                'active_view':'slider',
                'auto_slider':true,
                'slider_time':4,
                'default_stemplate_id':'theme_alan.m_product_slider',
                'default_gtemplate_id':'theme_alan.m_product_grid',
                'template_id':'theme_alan.m_product_slider',
                'slider_style':'as-mm-product-snippet-1',
                'grid_style':'as-mm-product-snippet-1',
                'col_item':4,
                'slider':true,
                'grid':true,
            }
        }

        useSubEnv({"MegaMenuProduct":this})
    }
}

MegaMenuProduct.template = 'theme_alan.m_product_configuration';
MegaMenuProduct.components = { SelectData };

export default {
    MegaMenuProduct: MegaMenuProduct,
}
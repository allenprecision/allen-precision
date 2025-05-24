/** @odoo-module alias=theme_alan.ProductSlider **/

import { SelectData } from "theme_alan.SelectData";

const { Component, useSubEnv } = owl;

class ProductSlider extends Component {
    setup(){
        /** Setup Method  */
        // Required to go back
        useSubEnv({'SnippetPicker':this.env.SnippetPicker})

        // Frame Columne Size
        this.props.col_size = this.env.SnippetBox.props.col_size;
        // Select Config Identifier
        this.props.selete_data_config = "ProductSlider"
        // Search
        this.props.search = "product.template";
        // Quick Search Option
        this.props.quick_search = ['newest','top_rated','best_seller']

        // Slider Styles
        this.props.slider_styles = [['Slider Style 1','theme_alan.s_product_slider', 'as-slider-1'],
        ['Slider Style 2','theme_alan.s_product_slider', 'as-slider-2'],
        ['Slider Style 3','theme_alan.s_product_slider', 'as-slider-3'],
        ['Slider Style 4','theme_alan.s_product_slider', 'as-slider-4'],
        ['Slider Style 5','theme_alan.s_product_slider', 'as-slider-5']]

        // Grid Styles
        this.props.grid_styles = [['Slider Style 1','theme_alan.s_product_grid', 'as-grid-1'],
           ['Slider Style 2','theme_alan.s_product_grid', 'as-grid-2'],
           ['Slider Style 3','theme_alan.s_product_grid', 'as-grid-3'],
           ['Slider Style 4','theme_alan.s_product_grid', 'as-grid-4'],
           ['Slider Style 5','theme_alan.s_product_grid', 'as-grid-5']]

        // Pagination Style
        this.props.pagination = [
            ['none', 'None'],
            ['simple', 'Simple'],
            ['dynamic', 'Dynamic'],
            ['progress_bar', 'Progress Bar'],
            ['fraction', 'Fraction'],
            ['scroll_bar', 'Scrollbar'],
            ['coverflow', 'Coverflow'],
            ['cards', 'Cards'],
        ]

        // Design and Edit option
        if(this.env.SnippetBox.props.initData != undefined){
            this.props.design_and_edit = this.env.SnippetBox.props.initData.design_edit;
            this.props.init_record_ids = this.env.SnippetBox.props.initData.record_ids;
        }else{
            this.props.design_and_edit = {
                'snippet':'ProductSlider',
                'frame_col':this.props.col_size,
                'grid_style':'as-grid-1',
                'slider_style':'as-slider-1',
                'default_stemplate_id':'theme_alan.s_product_slider',
                'default_gtemplate_id':'theme_alan.s_product_grid',
                'template_id':'theme_alan.s_product_slider',
                'view':'slider',
                'loop':true,
                'auto_slider':true,
                'slider_time': 3,
                'default_col_desk': 4,
                'default_col_mob': 2,
                'pagination':'none',
                'allow_add_to_cart': true,
                'allow_quick_view': true,
                'allow_compare': true,
                'allow_wishlist': false,
                'allow_rating': false,
                'allow_label': false,
                'allow_hover_image': false,
                'allow_stock_info': false,
                'allow_offer_time': false,
                'allow_brand_info': false,
                'allow_color_variant': false,

            }
        }

        useSubEnv({"ProductSlider":this})
    }
}

ProductSlider.template = 'theme_alan.s_product_configuration';
ProductSlider.components = { SelectData };

export default {
    ProductSlider: ProductSlider,
}
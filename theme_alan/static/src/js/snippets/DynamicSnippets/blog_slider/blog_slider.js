/** @odoo-module alias=theme_alan.BlogSlider **/

import { SelectData } from "theme_alan.SelectData";

const { Component, useSubEnv } = owl;

class BlogSlider extends Component {
    setup(){
        /** Setup Method */

        // Required to go back
        useSubEnv({'SnippetPicker':this.env.SnippetPicker})

        // Frame Columne Size
        this.props.col_size = this.env.SnippetBox.props.col_size;
        // Select Config Identifier
        this.props.selete_data_config = "BlogSlider"
        // Search
        this.props.search = "blog.post";
        // Quick Search Option
        this.props.quick_search = []

        // Slider Styles
        this.props.slider_styles = [['Slider Style 1','theme_alan.s_blog_slider', 'as-slider-1'],
        ['Slider Style 2','theme_alan.s_blog_slider', 'as-slider-2'],
        ['Slider Style 3','theme_alan.s_blog_slider', 'as-slider-3'],
        ['Slider Style 4','theme_alan.s_blog_slider', 'as-slider-4'],
        ['Slider Style 5','theme_alan.s_blog_slider', 'as-slider-5']]

        // Grid Styles
        this.props.grid_styles = [['Slider Style 1','theme_alan.s_blog_grid', 'as-slider-1'],
           ['Slider Style 2','theme_alan.s_blog_grid', 'as-grid-2'],
           ['Slider Style 3','theme_alan.s_blog_grid', 'as-grid-3'],
           ['Slider Style 4','theme_alan.s_blog_grid', 'as-grid-4'],
           ['Slider Style 5','theme_alan.s_blog_grid', 'as-grid-5']]

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
                'snippet':'BlogSlider',
                'frame_col':this.props.col_size,
                'grid_style':'as-grid-1',
                'slider_style':'as-slider-1',
                'default_stemplate_id':'theme_alan.s_blog_slider',
                'default_gtemplate_id':'theme_alan.s_blog_grid',
                'template_id':'theme_alan.s_blog_slider',
                'view':'slider',
                'loop':true,
                'auto_slider':true,
                'slider_time': 3,
                'default_col_desk': 4,
                'default_col_mob': 2,
                'pagination':'none',
            }
        }

        useSubEnv({"BlogSlider":this})
    }
}

BlogSlider.template = 'theme_alan.s_blog_configuration';
BlogSlider.components = { SelectData };

export default {
    BlogSlider: BlogSlider,
}
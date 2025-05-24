/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import options from "@web_editor/js/editor/snippets.options";
import Dialog from '@web/legacy/js/core/dialog';
import { _t } from '@web/core/l10n/translation';

const AlanWebsiteBuilder = Dialog.extend({
    willStart: function () {

        return this._super.apply(this, arguments).then(() => {
            switch (this.size) {
                case 'extra-large':
                    this.$modal.find('.modal-dialog').addClass('modal-xl');
                    break;
                case 'large':
                    this.$modal.find('.modal-dialog').addClass('modal-lg');
                    break;
                case 'small':
                    this.$modal.find('.modal-dialog').addClass('modal-sm');
                    break;
                case 'as-extra-large':
                    this.$modal.find('.modal-dialog').addClass('as-extra-large');
                    break;
            }
        });
    },
})

options.registry.alan_website_builder = options.Class.extend({
    xmlDependencies: ['/theme_alan/static/src/xml/website_builder/website_builder.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/homepage.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/sliders.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/banner.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/about.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/call_to_action.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/category.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/our_client.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/collection.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/contact_us.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/features.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/our_team.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/portfolio.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/price_table.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/promotion.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/services.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/shop_banner.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/testimonial.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/title_section.xml',
                      '/theme_alan/static/src/xml/website_builder/templates/video_popup.xml' ],
    events:{'click':'_changeCollection' },
    _changeCollection:function(){
        this.select_snippet('click','true');
    },
    select_snippet: function(type, value) {
        this.id = this.$target.attr('id');
        if(type == false || type == 'click'){
            var dialog = new AlanWebsiteBuilder(this, {
                size: 'as-extra-large',
                dialogClass:"as_website_builder",
                title: 'Alan Website Builder',
                $content: renderToElement('theme_alan.builder_block', {'uniq':Date.now() }),
                buttons: [{text: _t('Save'), classes: 'btn-primary', close: true, click: () => {
                    var snippet = $("input[name='radio-snippet']:checked").closest('.snippet-as').find('textarea').html();
                    this.$target.empty().append(snippet);
                    var model = this.$target.parent().attr('data-oe-model');
                    if(model){
                        this.$target.parent().addClass('o_editable o_dirty');
                    }
                    this.trigger_up('widgets_start_request', {
                        $target:$('.hero_slider')
                    });
                }}, {text: _t('Discard'), close: true}],
            });
            dialog.opened().then(()=>{
                dialog.$el.find(".edit-snippet-builder-box .e-sb-tab label").click( function(){
                    $('.edit-snippet-builder-box .e-sb-tab label').removeClass('e-sb-active');
                    $(this).addClass('e-sb-active');
                    var tagid = $(this).data('tag');
                    $('.e-sb-tab--content').removeClass('active').addClass('d-none');
                    $('#'+tagid).addClass('active').removeClass('d-none');
                });
            })
            dialog.open();
        }
    },
    onBuilt: function () {
        this._super();
        this.select_snippet('click', 'true');
    },
});

/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/website_sale";
import { _t } from '@web/core/l10n/translation';

VariantMixin._onChangeCombinationIntercalReference = function (ev, $parent, combination) {
    let $product_sku = this.$target.find(".as_product_sku");
    let $last_month_count = this.$target.find(".as_month_sale_count");
    let $as_bulk_save = this.$target.find(".as_bulk_save");
    let $offer_timer = this.$target.find(".as_offer_timer");
    if(combination.last_month_count > 0){
        let strs =  "<span><b>"+ combination.last_month_count + "</b>" +  _t(" sold in last month") + "</span>";
        $last_month_count.empty().html(strs);
    }else{
        $last_month_count.empty();
    }
    if(combination.bulk_save != false){
        $as_bulk_save.removeClass("d-none").empty().append($(combination.bulk_save));
    }else{
        $as_bulk_save.addClass("d-none").empty();
    }
    if(combination.offer_timer != false){
        $offer_timer.attr("data-offer", combination.offer_timer)
        this.trigger_up('widgets_start_request', {
            $target:$('.as_offer_timer')
        });
    }
    if(combination.default_code != false){
        var html = combination.default_code;
        $product_sku.find("span").empty().append(html);
        $product_sku.removeClass("d-none")
    }else{
        $product_sku.find("span").empty();
        $product_sku.addClass("d-none")
    }
}
publicWidget.registry.WebsiteSale.include({
    _onChangeCombination: function () {
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationIntercalReference.apply(this, arguments);
    },

});

export default VariantMixin;

/** @odoo-module */

import { registry } from '@web/core/registry';
import { loadXML } from '@web/core/utils/xml';
import { Component } from '@odoo/owl';
import VariantMixin from "@website_sale/js/sale_variant_mixin";

//const QWeb = core.qweb;

class GroupProductSale extends Component {
    static template = 'website_grouped_product.GroupProductSale';

    setup() {
        this._onChangeAddGrpQuantity = this._onChangeAddGrpQuantity.bind(this);
        this._onSubmitCombo = this._onSubmitCombo.bind(this);
    }

    /**
     * Handle quantity change for grouped products.
     */
    _onChangeAddGrpQuantity(ev) {
        VariantMixin.onChangeAddQuantity(ev);
    }

    /**
     * Prevent form submission for grouped products.
     */
    _onSubmitCombo(ev) {
        ev.preventDefault();
        return false;
    }
}

/**
 * Overriding the _onChangeCombination function for grouped product handling.
 */
VariantMixin._onChangeCombinationGroup = function (ev, $parent, combination) {
    const $price = $parent.find(".oe_price:first .oe_currency_value");
    const $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
    const $optional_price = $parent.find(".oe_optional:first .oe_currency_value");

    let isCombinationPossible = combination.is_combination_possible ?? true;

    this._toggleDisable($parent, isCombinationPossible);

    $price.html(VariantMixin._priceToStr(combination.price));
    $default_price.html(VariantMixin._priceToStr(combination.list_price));

    if (combination.has_discounted_price) {
        $default_price.closest('.oe_website_sale').addClass("discount");
        $optional_price.closest('.oe_optional').removeClass('d-none').css('text-decoration', 'line-through');
        $default_price.parent().removeClass('d-none');
    } else {
        $default_price.closest('.oe_website_sale').removeClass("discount");
        $optional_price.closest('.oe_optional').addClass('d-none');
        $default_price.parent().addClass('d-none');
    }

    const isGroupChild = combination.product_id && $parent.is('.p_variant');

    if (isGroupChild) {
        let qty = $parent.find('input[name="add_qty"]').val();

        $parent.parent().parent().next().next().find('#buy_now').removeClass('disabled out_of_stock');
        $parent.parent().parent().next().next().find('#add_to_cart').removeClass('disabled out_of_stock');

        if (combination.product_type === 'product' && ['always', 'threshold'].includes(combination.inventory_availability)) {
            combination.virtual_available -= parseInt(combination.cart_qty, 10);
            combination.virtual_available = Math.max(0, combination.virtual_available);

            if (qty > combination.virtual_available) {
                const $input_add_qty = $parent.find('input[name="add_qty"]');
                qty = combination.virtual_available || 1;
                $input_add_qty.val(qty);
            }

            if (qty > combination.virtual_available || combination.virtual_available < 1 || qty < 1) {
                $parent.find('#add_to_cart').addClass('disabled out_of_stock');
                $parent.find('#buy_now').addClass('disabled out_of_stock');
            }
        }

//        loadXML('/website_sale_stock/static/src/xml/website_sale_stock_product_availability.xml', QWeb).then(() => {
//            const $message = $(QWeb.render('website_sale_stock.product_availability', combination));
//            $parent.find('div.availability_messages').html($message);
//        });
    }
};

/**
 * Extend WebsiteSale to override _onChangeCombination method.
 */
registry.category('actions').add('website_sale', {
    _onChangeCombination(ev, $parent, combination) {
        if ($("div.p_variant").length === 0) {
            this._super(ev, $parent, combination);
        } else {
            VariantMixin._onChangeCombinationGroup(ev, $parent, combination);
        }
    },
});

export default GroupProductSale;

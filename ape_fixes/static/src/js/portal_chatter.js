/** @odoo-module **/

import PortalChatter from "@portal/js/portal_chatter";

/**
 * Hide the entire chatter section (messages, composer, headings, etc.)
 * for portal users who don't have a confirmed sale order.
 *
 * The `hide_chatter` option is set by the overridden /mail/chatter_init
 * controller in ape_fixes.
 */
var originalStart = PortalChatter.prototype.start;

PortalChatter.prototype.start = function () {
    var self = this;
    return Promise.resolve(originalStart.apply(this, arguments)).then(function () {
        if (self.options.restrict_chatter_composer) {
            self._hideChatterSection();
        }
    });
};

/**
 * Hide the chatter and its surrounding section container so that
 * headings like "Communication history" and "Customer Reviews"
 * are also hidden.
 */
PortalChatter.prototype._hideChatterSection = function () {
    // Hide the standard portal composer (input box)
    this.$el.find('.o_portal_chatter_composer').hide();
    
    // Hide the rating popup composer (stars/Add Review button on product pages)
    // We look for it globally or relative to the parent because it might be a separate peer widget
    var $container = this.$el.parent();
    $container.find('.o_rating_popup_composer').hide();
    
    // Fallback/Generic: hide any composer inside the chatter
    this.$('.o_portal_chatter_composer').hide();
};



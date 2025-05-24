/** @odoo-module alias=theme_alan.mixins **/

import { renderToElement } from "@web/core/utils/render";

var alanTemplate = {
    getStaticTemplate:function(template, context){
        return renderToElement(template, { data: context });
    }
}

export default {
    alanTemplate:alanTemplate,
}

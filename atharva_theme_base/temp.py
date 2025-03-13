from odoo import api, SUPERUSER_ID

def add_fields(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Get the website model ID
    website_model = env['ir.model'].search([('model', '=', 'website')], limit=1)
    if not website_model:
        print("Model 'website' not found!")
        return

    # Get the product.template model ID
    product_model = env['ir.model'].search([('model', '=', 'product.template')], limit=1)
    if not product_model:
        print("Model 'product.template' not found!")
        return

    # Define the new fields
    new_fields = [
        {
            'name': 'is_advance_megamenu',
            'ttype': 'boolean',
            'field_description': 'Enable Advanced Mega Menu',
            'model_id': website_model.id,
        },
        {
            'name': 'is_pwa_active',
            'ttype': 'boolean',
            'field_description': 'PWA',
            'model_id': website_model.id,
        },
        {
            'name': 'active_login_popup',
            'ttype': 'boolean',
            'field_description': 'Enable Login Popup',
            'model_id': website_model.id,
        },

    ]

    model_field = env['ir.model.fields']

    for field in new_fields:
        if not model_field.search([('name', '=', field['name']), ('model_id', '=', field['model_id'])]):
            model_field.create(field)

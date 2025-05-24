# -*- coding: utf-8 -*-

from odoo import fields, models

class SnippetFrame(models.Model):
    _name = "as.snippet.frame"
    _description = "Snippet Frames"

    name = fields.Char()
    snippet_frame = fields.Text(required=True)
    snippet_frame_html = fields.Html(required=True)

class SnippetFrameConfigure(models.Model):
    _name = "as.snippet.frame.config"
    _description = "Snippet Frame Configure Data"

    name = fields.Text(required=True)
    snippet_frame_config = fields.Text(required=True)
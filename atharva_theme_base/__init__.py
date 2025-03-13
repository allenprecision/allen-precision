# -*- coding: utf-8 -*-

from . import models
from .temp import add_fields


def pre_init_hook(cr):
    add_fields(cr)  # Execute field creation before module installation

def post_init_hook(cr, registry):
    add_fields(cr)  # Execute after module is installed

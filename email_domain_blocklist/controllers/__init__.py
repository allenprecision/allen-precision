# The checkout controller only makes sense when website_sale is installed.
# Import is wrapped so the module still loads on a backend-only database.
try:
    from . import main
except ImportError:
    pass

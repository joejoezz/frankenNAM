"""python site/render ...   (or: cd site && python -m render ...)
The directory is named `site/` as the brief asks, which shadows nothing when run this way, but
`python -m site.render` cannot work: `site` is a standard-library module Python imports at startup."""
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from render.cli import main
else:
    from .cli import main

main()

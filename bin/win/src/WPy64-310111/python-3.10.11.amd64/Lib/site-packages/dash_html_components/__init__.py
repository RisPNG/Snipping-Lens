from dash.html import *  # noqa: F401, F403, E402
from dash.html import __version__  # noqa: F401, F403, E402
import warnings

warnings.warn(
    """
The dash_html_components package is deprecated. Please replace
`import dash_html_components as html` with `from dash import html`""",
    stacklevel=2,
)

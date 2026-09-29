from dotenv import load_dotenv

load_dotenv()

import reflex as rx
import reflex_xy

config = rx.Config(
    app_name="autonomous_pipeline_incident_ui",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        reflex_xy.XYPlugin(),
    ],
)

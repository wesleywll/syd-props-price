from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import json
from src.paths import DATA_DIR, LOC_BOUND_PATH
import os
import seaborn as sns
import matplotlib.pyplot as plt
from plotly.tools import mpl_to_plotly

# import data
dataset = pd.read_csv(os.path.join(DATA_DIR, "dataset.csv"))  # cleaned dataset
loc_bound = json.load(open(LOC_BOUND_PATH, "r"))  # locality boundaries geojson


def trim_loc_bound(df, loc_bound):
    zones = df.locality.unique()
    loc_bound_trimmed = loc_bound.copy()
    loc_bound_trimmed["features"] = [
        feat
        for feat in loc_bound["features"]
        if feat["properties"]["nsw_loca_2"] in zones
    ]
    return loc_bound_trimmed


def get_loc_map(df, loc_bound, color_by="slope"):
    fig = px.choropleth_mapbox(
        df.reset_index(),
        geojson=loc_bound,
        featureidkey="properties.nsw_loca_2",
        locations="locality",
        color=color_by,
        opacity=0.6,
        center=dict(lat=-33.869844, lon=151.208285),
        # height=600,
        # width=800,
        color_continuous_scale="Inferno",
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 5, "l": 0, "b": 5})
    return fig


def get_trend_plot(df, loc):
    df_plot = (
        df[df.locality == loc].groupby(["property_type", "year"]).median().reset_index()
    )
    fig = px.line(
        df_plot,
        x="year",
        y="price",
        color="property_type",
        title=loc,
    )
    return fig


# data processing
loc_bound_trimmed = trim_loc_bound(dataset, loc_bound)
price_by_loc = (
    dataset.query("0<price <=1.5e6")[["locality", "price"]].groupby("locality").median()
)


# rendering
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container(
    children=[
        dbc.Row(
            [
                dbc.Col(html.Div(dcc.Graph(id="click-display")), width=6),
                dbc.Col(
                    html.Div(
                        dcc.Graph(
                            id="loc-map",
                            figure=get_loc_map(
                                price_by_loc, loc_bound_trimmed, "price"
                            ),
                            style={"width": "45vw", "height": "100vh"},
                        )
                    ),
                    width=6,
                ),
            ],
            justify="between",
            align='center',
        )
    ]
)


# callbacks
@app.callback(Output("click-display", "figure"), Input("loc-map", "clickData"))
def display_click_data(clickData):
    if clickData:
        loc = clickData.get("points")[0].get("location")
        return get_trend_plot(dataset, loc)
    else:
        return {}


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", debug=True)

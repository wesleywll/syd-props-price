from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import numpy as np
import json
from src.paths import DATA_DIR, LOC_BOUND_PATH, AUS_PATH
import os
from plotly.tools import mpl_to_plotly
from src.paths import DATA_DIR, LOC_BOUND_PATH, SUBURB_COORD_PATH
from src.func import log_regress, dist, million, percent


def trim_geojson(geojson, select: list):
    # get trimmed geojson with provided localities
    trimmed = geojson.copy()
    trimmed["features"] = [
        feat
        for feat in geojson["features"]
        if feat["properties"]["nsw_loca_2"] in select
    ]
    return trimmed


def get_loc_map(df, loc_bound, color_key, title=""):
    fig = px.choropleth_mapbox(
        df.reset_index(),
        geojson=loc_bound,
        featureidkey="properties.nsw_loca_2",
        locations="locality",
        color=color_key,
        opacity=0.6,
        center=dict(lat=-33.869844, lon=151.208285),
        # height=600,
        # width=800,
        color_continuous_scale=[
            (0, "#0240fa"),
            (0.5, "#14fa00"),
            (1, "#fa6000"),
        ],
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=title,
            x=-0.02,
            ticklabelposition="inside",
        )
    )
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


# ----------------------------------
# -- import data
df_rec = pd.read_csv(os.path.join(DATA_DIR, "dataset.csv"))  # cleaned sales records
json_bound = json.load(open(LOC_BOUND_PATH, "r"))  # locality boundaries geojson
df_sub = pd.read_csv(
    os.path.join(AUS_PATH, "nsw_suburb_coord.csv")
)  # coordinates of suburbs
CBD_COORD = (-33.8708, 151.2073)  # coordinates of Sydney CBD

# -- data processing
# get suburb list
suburbs = df_rec.locality.unique().tolist()[:10]
# trim boundary data to reduce load time
json_bound_trim = trim_geojson(geojson=json_bound, select=suburbs)

# annual median price of all suburbs
df_all_med = (
    df_rec.groupby(["locality", "property_type", "year"]).median().reset_index()
)

# calculate distance from CBD
df_sub["dist"] = df_sub.apply(
    lambda row: dist(row["lat"], row["lon"], CBD_COORD[0], CBD_COORD[1]), axis=1
)

# apply regression to find annual growth rate
results = df_all_med.groupby(["locality", "property_type"]).apply(log_regress)
results["annual_rate"] = np.exp(results.slope) - 1
results = results.unstack()
results.columns = ["_".join(col_pair) for col_pair in results.columns]
results.reset_index(inplace=True)
# merge results into suburb data
df_sub = pd.merge(df_sub, results, on="locality", how="left")

# -- Summary --
# df_all_med: contains medians of all suburbs, grouped by locality, property_type and year
# df_sub: contains details of suburbs, including coordinates, CBD distance and regression results

# ----------------------------------
# rendering
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[dict(name="viewport", content="width=device-width, initial-scale=1.0")],
)
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.Button(
                                id="map_toggle_button",
                                n_clicks=0,
                                className="bg-dark",
                                children="Toggle Map",
                            ),
                            dbc.Collapse(
                                id="map_collapse",
                                is_open=True,
                                children=dbc.CardBody(
                                    children=[
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    width=6,
                                                    className='radio-group',
                                                    children=[
                                                        dbc.RadioItems(
                                                            id="map_option_radio_datakey",
                                                            className="btn-group d-flex flex-grow-1 justify-content-center",
                                                            inputClassName="btn-check",
                                                            labelClassName="btn btn-outline-secondary",
                                                            labelCheckedClassName="active",
                                                            options=[
                                                                dict(
                                                                    label="Price",
                                                                    value="price",
                                                                ),
                                                                dict(
                                                                    label="Rate",
                                                                    value="rate",
                                                                ),
                                                            ],
                                                            value="price",
                                                        )
                                                    ],
                                                ),
                                                dbc.Col(
                                                    width=6,
                                                    className='radio-group',
                                                    children=[
                                                        dbc.RadioItems(
                                                            id="map_option_radio_prop_type",
                                                            className="btn-group d-flex flex-grow-1 justify-content-center",
                                                            inputClassName="btn-check",
                                                            labelClassName="btn btn-outline-secondary",
                                                            labelCheckedClassName="active",
                                                            options=[
                                                                dict(
                                                                    label="House",
                                                                    value="House",
                                                                ),
                                                                dict(
                                                                    label="Unit",
                                                                    value="Unit",
                                                                ),
                                                            ],
                                                            value="Unit",
                                                        ),
                                                    ],
                                                ),
                                            ]
                                        ),
                                        dcc.Graph(
                                            id="loc-map",
                                            figure=get_loc_map(
                                                df_all_med,
                                                json_bound_trim,
                                                color_key="price",
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                        ]
                    ),
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                ),
                dbc.Col(
                    dbc.Card([dbc.CardBody(dcc.Graph(id="click-display"))]),
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                ),
            ],
            justify="between",
            align="top",
        )
    ],
    fluid=True,
)


# callbacks
@app.callback(Output("click-display", "figure"), Input("loc-map", "clickData"))
def display_click_data(clickData):
    # show chart for the suburb clicked on map
    if clickData:
        loc = clickData.get("points")[0].get("location")
        return get_trend_plot(df_rec, loc)
    else:
        return {}


@app.callback(
    Output("map_collapse", "is_open"),
    Input("map_toggle_button", "n_clicks"),
    State("map_collapse", "is_open"),
)
def toggle_map_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", debug=True)

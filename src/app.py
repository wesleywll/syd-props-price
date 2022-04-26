from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import json
from src.paths import DATA_DIR, LOC_BOUND_PATH
import os
from plotly.tools import mpl_to_plotly
from src.paths import DATA_DIR, LOC_BOUND_PATH, SUBURB_COORD_PATH

# import data
dataset = pd.read_csv(os.path.join(DATA_DIR, "dataset.csv"))  # cleaned dataset
loc_bound = json.load(open(LOC_BOUND_PATH, "r"))  # locality boundaries geojson


def get_trimmed_bound_data(localities: list):
    # get trimmed geojson with provided localities
    loc_bound_trimmed = loc_bound.copy()
    loc_bound_trimmed["features"] = [
        feat
        for feat in loc_bound["features"]
        if feat["properties"]["nsw_loca_2"] in localities
    ]
    return loc_bound_trimmed


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
            (0.5, '#14fa00'),
            (1, "#fa6000"),
        ],
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=title,
            x=-0.02,
            ticklabelposition='inside',
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


# data processing
localities = dataset.locality.unique().tolist()
loc_bound_trimmed = get_trimmed_bound_data(localities[:10])
price_by_loc = (
    dataset.query("0<price <=3e6")[["locality", "price"]].groupby("locality").median()
)


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
                                        dbc.RadioItems(
                                            id="map_option_radio",
                                            className="btn-group d-flex flex-grow-1 justify-content-center",
                                            inputClassName="btn-check",
                                            labelClassName="btn btn-outline-primary",
                                            labelCheckedClassName="active",
                                            options=[
                                                dict(
                                                    label="Median Price", value="price"
                                                ),
                                                dict(label="Growth Rate", value="rate"),
                                            ],
                                            value="price",
                                        ),
                                        dcc.Graph(
                                            id="loc-map",
                                            figure=get_loc_map(
                                                price_by_loc,
                                                loc_bound_trimmed,
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
            align="center",
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
        return get_trend_plot(dataset, loc)
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

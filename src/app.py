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


# ----------------------------------
# -- import data
df_rec = pd.read_csv(os.path.join(DATA_DIR, "dataset.csv"))  # cleaned sales records
json_bound = json.load(open(LOC_BOUND_PATH, "r"))  # locality boundaries geojson
df_sub = pd.read_csv(
    os.path.join(AUS_PATH, "nsw_suburb_coord.csv")
)  # coordinates of suburbs
CBD_COORD = (-33.8708, 151.2073)  # coordinates of Sydney CBD

# -- data processing
# annual median price of all suburbs
df_all_med = (
    df_rec.groupby(["locality", "property_type", "year"])
    .median()
    .reset_index()
    .sort_values(by=["locality", "property_type", "year"])
)
# calculate price and year difference between consecutive rows
price_diff = df_all_med.groupby(["locality", "property_type"]).price.diff()
year_diff = df_all_med.groupby(["locality", "property_type"]).year.diff()
# extrapolate change rate in case of missing years
df_all_med["rate"] = (price_diff / df_all_med.price.shift(1)) / year_diff

# calculate distance from CBD
df_sub["dist"] = df_sub.apply(
    lambda row: dist(row["lat"], row["lon"], CBD_COORD[0], CBD_COORD[1]), axis=1
)
# get suburb list
CBD_DIST = 60  # max suburb distance from CBD (km)
suburbs = df_sub.query(f"dist <= {CBD_DIST}").locality.unique().tolist()
# trim boundary data to reduce load time
json_bound_trim = trim_geojson(geojson=json_bound, select=suburbs)

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
    fluid=True,
    children=[
        dbc.Row(
            justify="center",
            align="top",
            children=[
                dbc.Col(
                    dbc.Card(
                        children=[
                            dbc.Button(
                                id="map_toggle_button",
                                n_clicks=0,
                                className="bg-dark card-title",
                                children="Hide Map",
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
                                                    className="radio-group",
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
                                                    className="radio-group",
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
                                        dbc.Row(
                                            justify="center",
                                            children=[
                                                dcc.Slider(
                                                    id="year_slider",
                                                    min=2000,
                                                    max=2021,
                                                    step=1,
                                                    value=2021,
                                                    marks={
                                                        2000: dict(label="2000"),
                                                        2008: dict(label="2008"),
                                                        2019: dict(label="2019"),
                                                        2021: dict(label="2021"),
                                                    },
                                                    tooltip={
                                                        "placement": "top",
                                                        "always_visible": True,
                                                    },
                                                    className="pt-5 ",
                                                )
                                            ],
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(id="fig_data_map"),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                ),
            ],
        ),
        dbc.Row(
            justify="center",
            align="top",
            children=[
                dbc.Col(
                    children=[
                        dcc.Loading(
                            dbc.Card([dbc.CardBody(dcc.Graph(id="fig_price_trend"))])
                        ),
                    ],
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                ),
                dbc.Col(
                    children=[
                        dcc.Loading(
                            dbc.Card([dbc.CardBody(dcc.Graph(id="fig_rate_trend"))])
                        ),
                    ],
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                ),
            ],
        ),
        # stores for shared values
        dcc.Store(id="locality"),
        dcc.Store(id="year"),
        dcc.Store(id="prop_type"),
        dcc.Store(id="data_type"),
    ],
)


# ------------------
# plot functions
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
            x=-0.01,
            ticklabelposition="inside",
        )
    )
    fig.update_layout(margin={"r": 0, "t": 5, "l": 0, "b": 5})
    return fig


# ----------------------------
# --- map callbacks
@app.callback(
    [Output("map_collapse", "is_open"), Output("map_toggle_button", "children")],
    Input("map_toggle_button", "n_clicks"),
    State("map_collapse", "is_open"),
)
def toggle_map_collapse(n_clicks, is_open):
    txt = "Hide Map" if is_open else "Show Map"
    if n_clicks:
        new_is_open = not is_open
        txt = "Hide Map" if new_is_open else "Show Map"
        return new_is_open, txt
    return is_open, txt


@app.callback(
    Output("fig_data_map", "figure"),
    [
        Input("map_option_radio_datakey", "value"),
        Input("map_option_radio_prop_type", "value"),
        Input("year_slider", "value"),
    ],
)
def change_data_map(datakey, prop_type, year=2021):
    if datakey == "price":
        df = pd.merge(
            df_sub,
            df_all_med.query(f"property_type=='{prop_type}' & year=={year}")[
                ["locality", "price"]
            ],
            on="locality",
            how="left",
        )
        return get_loc_map(df, json_bound_trim, color_key=datakey)
    elif datakey == "rate":
        return get_loc_map(
            df_sub, json_bound_trim, color_key=f"annual_rate_{prop_type}"
        )


@app.callback(Output("locality", "data"), Input("fig_data_map", "clickData"))
def map_clicked(clickData):
    # data map clicked, update locality in store
    if clickData:
        loc = clickData.get("points")[0].get("location")
    else:
        loc = "SYDNEY"  # default locality
    return dict(locality=loc)


# --- plots callbacks
@app.callback(Output("fig_price_trend", "figure"), Input("locality", "data"))
def plot_suburb_price_trend(data):
    # locality changed, update plot
    loc = data.get("locality")
    df_plot = df_all_med.query(f'locality=="{loc}"')
    fig = px.line(
        df_plot,
        x="year",
        y="price",
        color="property_type",
        title=loc.title(),
    )
    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig


@app.callback(Output("fig_rate_trend", "figure"), Input("locality", "data"))
def plot_suburb_rate_trend(data):
    # locality changed, update plot
    loc = data.get("locality")
    df_plot = df_all_med.query(f'locality=="{loc}"')
    fig = px.line(
        df_plot,
        x="year",
        y="rate",
        color="property_type",
        title=loc.title(),
    )
    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", debug=True)

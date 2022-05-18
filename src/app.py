from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
from src.paths import DATA_DIR, LOC_BOUND_PATH, AUS_PATH
import os
from plotly.tools import mpl_to_plotly
from src.paths import DATA_DIR, LOC_BOUND_PATH, SUBURB_COORD_PATH
from src.func import log_regress, dist, million, percent

PRIMARY_COLOR = "#3891ff"
SECONDARY_COLOR = "#b0bfec"
PROP_COLOR = dict(House=SECONDARY_COLOR, Unit=PRIMARY_COLOR)
PLOT_BG_COLOR = "#eeeeee"


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
# coordinates of suburbs
df_sub_coords = pd.read_csv(os.path.join(AUS_PATH, "nsw_suburb_coord.csv"))
# coordinates of Sydney CBD
CBD_COORD = (-33.8708, 151.2073)

# -- data processing
def get_filtered_sub_med(
    df_in: pd.DataFrame,
    loc: str = None,
    price_range: list = None,
    bed_range: list = None,
):
    # filter data
    df = df_in.copy()
    if loc:
        df = df[df.locality == loc]
    if price_range:
        p_range = [p * 1e6 for p in price_range]  # convert million to exact numbers
        df = df[df.price.isin(p_range)]
    if bed_range:
        df = df[df.bedrooms.isin(bed_range)]
    df = (
        df.groupby(["locality", "property_type", "year"])
        .median()
        .reset_index()
        .sort_values(by=["locality", "property_type", "year"])
    )
    # calculate change rate
    price_diff = df.groupby(["locality", "property_type"]).price.diff()
    year_diff = df.groupby(["locality", "property_type"]).year.diff()
    # extrapolate change rate in case of missing years
    df["rate"] = (price_diff / df.price.shift(1)) / year_diff
    return df


def get_sub_summary(df_sub_coords: pd.DataFrame, df_med_trend: pd.DataFrame):
    # filter data
    df = df_sub_coords.copy()
    # calculate distance from CBD
    df["dist"] = df.apply(
        lambda row: dist(row["lat"], row["lon"], CBD_COORD[0], CBD_COORD[1]), axis=1
    )

    # apply regression to find annual growth rate
    results = df_med_trend.groupby(["locality", "property_type"]).apply(log_regress)
    results["annual_rate"] = np.exp(results.slope) - 1
    results = results.unstack()
    results.columns = ["_".join(col_pair) for col_pair in results.columns]
    results.reset_index(inplace=True)
    # merge results into suburb data
    df = pd.merge(df, results, on="locality", how="left")
    return df


# annual median price of all suburbs
df_med_trend = get_filtered_sub_med(df_rec)
df_sub_smry = get_sub_summary(df_sub_coords, df_med_trend)

# -- Summary --
# df_med_trend: contains median trends of all suburbs, grouped by locality, property_type and year
# df_sub_smry: contains summary details of suburbs, including coordinates, CBD distance and regression results

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
                                                        y: str(y)
                                                        for y in [
                                                            2000,
                                                            2008,
                                                            2019,
                                                            2021,
                                                        ]
                                                    },
                                                    tooltip={
                                                        "placement": "top",
                                                        "always_visible": True,
                                                    },
                                                    className="pt-5 ",
                                                ),
                                                dcc.RangeSlider(
                                                    id="dist_slider",
                                                    min=0,
                                                    max=100,
                                                    step=1,
                                                    value=[0, 10],
                                                    marks={
                                                        d: f"{d} km"
                                                        for d in [0, 20, 40, 70, 100]
                                                    },
                                                    tooltip={
                                                        "placement": "top",
                                                    },
                                                ),
                                                dcc.RangeSlider(
                                                    id="price_slider",
                                                    min=0.1,
                                                    max=3,
                                                    step=0.1,
                                                    value=[0.5, 2],
                                                    marks={
                                                        d: f"{d:.1f} M"
                                                        for d in [
                                                            0.1,
                                                            0.5,
                                                            1,
                                                            1.5,
                                                            2,
                                                            2.5,
                                                            3,
                                                        ]
                                                    },
                                                    tooltip={
                                                        "placement": "top",
                                                    },
                                                ),
                                            ],
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="fig_data_map",
                                                config=dict(displayModeBar=False),
                                            ),
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
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                    children=[
                        dcc.Loading(
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        children=[
                                            dbc.Row(
                                                children=[
                                                    html.P("Bedrooms"),
                                                    dcc.RangeSlider(
                                                        id="bed_slider",
                                                        min=0,
                                                        max=5,
                                                        step=1,
                                                        value=[1, 3],
                                                        tooltip={
                                                            "placement": "top",
                                                        },
                                                    ),
                                                ]
                                            ),
                                            dbc.Row(
                                                children=[
                                                    dcc.Graph(
                                                        id="fig_sub_trend",
                                                        config=dict(
                                                            displayModeBar=False
                                                        ),
                                                    ),
                                                ]
                                            ),
                                        ],
                                    )
                                ]
                            )
                        ),
                    ],
                ),
                dbc.Col(
                    xs=12,
                    sm=12,
                    md=12,
                    lg=6,
                    xl=6,
                    children=[
                        dcc.Loading(
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        children=[
                                            dbc.Row(
                                                justify="center",
                                                align="bottom",
                                                children=[
                                                    dbc.Col(
                                                        width=6,
                                                        children=[
                                                            html.P("Bedrooms"),
                                                            dcc.RangeSlider(
                                                                id="dist_bed_slider",
                                                                min=0,
                                                                max=5,
                                                                step=1,
                                                                value=[1, 3],
                                                                tooltip={
                                                                    "placement": "top",
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                    dbc.Col(
                                                        width=6,
                                                        children=[
                                                            html.P("Year"),
                                                            dcc.Slider(
                                                                id="dist_year_slider",
                                                                min=2000,
                                                                max=2021,
                                                                step=1,
                                                                value=2021,
                                                                marks={
                                                                    y: str(y)
                                                                    for y in [
                                                                        2000,
                                                                        2021,
                                                                    ]
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            dbc.Row(
                                                [
                                                    dcc.Graph(
                                                        id="fig_sub_dist",
                                                        config=dict(
                                                            displayModeBar=False
                                                        ),
                                                    )
                                                ]
                                            ),
                                        ]
                                    )
                                ]
                            )
                        )
                    ],
                ),
            ],
        ),
        # stores for shared values
        dcc.Store(id="locality"),
        dcc.Store(id="year"),
        dcc.Store(id="prop_type"),
        dcc.Store(id="data_type"),
        dcc.Store(id="geojson"),
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


# filter suburbs shown on map
@app.callback(
    Output("geojson", "data"),
    [
        Input("dist_slider", "value"),
    ],
)
def suburb_filter_changed(dist_range):
    # get suburb list
    dist_min, dist_max = dist_range
    suburbs = (
        df_sub_smry.query(f"{dist_min} <= dist <= {dist_max}")
        .locality.unique()
        .tolist()
    )
    # trim boundary data to reduce load time
    json_bound_trim = trim_geojson(geojson=json_bound, select=suburbs)
    return json_bound_trim


# change map
@app.callback(
    Output("fig_data_map", "figure"),
    [
        Input("map_option_radio_datakey", "value"),
        Input("map_option_radio_prop_type", "value"),
        Input("year_slider", "value"),
        Input("price_slider", "value"),
        Input("geojson", "data"),
    ],
)
def change_data_map(datakey, prop_type, year, price_range, geojson):
    if datakey == "price":
        price_min = price_range[0] * 1e6
        price_max = price_range[1] * 1e6

        df = pd.merge(
            df_sub_smry,
            df_med_trend.query(
                f"property_type=='{prop_type}' & year=={year} & {price_min}<= price <= {price_max}"
            )[["locality", "price"]],
            on="locality",
            how="left",
        )
        return get_loc_map(df, geojson, color_key=datakey)
    elif datakey == "rate":
        return get_loc_map(df_sub_smry, geojson, color_key=f"annual_rate_{prop_type}")


@app.callback(Output("locality", "data"), Input("fig_data_map", "clickData"))
def map_clicked(clickData):
    # data map clicked, update locality in store
    if clickData:
        loc = clickData.get("points")[0].get("location")
    else:
        loc = "SYDNEY"  # default locality
    return dict(locality=loc)


# --- plots callbacks
@app.callback(
    Output("fig_sub_trend", "figure"),
    [
        Input("locality", "data"),
        Input("bed_slider", "value"),
    ],
)
def plot_suburb_trend(data, bed_range):
    # locality changed, update plot
    loc = data.get("locality")
    df_plot = get_filtered_sub_med(df_rec, loc=loc, bed_range=bed_range)
    fig = make_subplots(
        rows=2,
        cols=1,
        vertical_spacing=0.02,
        shared_xaxes=True,
    )

    for prop in df_plot.property_type.unique():
        df = df_plot[df_plot.property_type == prop]
        # price trend
        fig.add_trace(
            go.Scatter(
                x=df.year,
                y=df.price,
                name=prop,
                mode="lines+markers",
                marker_color=PROP_COLOR[prop],
            ),
            row=1,
            col=1,
        )
        # rate trend
        fig.add_trace(
            go.Bar(
                x=df.year,
                y=df.rate,
                name=prop,
                marker_color=PROP_COLOR[prop],
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    fig.update_layout(plot_bgcolor=PLOT_BG_COLOR)
    fig.update_layout(title=f"{loc.title()} price trend")
    # control subplot proportion
    rate_height = 0.25
    gap = 0.02
    fig.update_layout(
        yaxis=dict(domain=[rate_height + gap, 1]),
        yaxis2=dict(domain=[0, rate_height]),
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_yaxes(title_text="Median price", row=1, col=1)
    fig.update_yaxes(title_text="Changes", row=2, col=1, tickformat=".0%")
    fig.update_layout(
        margin=dict(
            t=30,
            r=0,
            b=0,
            l=0,
        ),
    )
    return fig


@app.callback(
    Output("fig_sub_dist", "figure"),
    [
        Input("locality", "data"),
        Input("dist_bed_slider", "value"),
        Input("dist_year_slider", "value"),
    ],
)
def plot_suburb_dist(data, bed_range, year):
    # locality changed, update plot
    loc = data.get("locality")
    bmin, bmax = bed_range
    df_plot = df_rec.query(f"locality=='{loc}' & year=={year} & {bmin} <= bedrooms <= {bmax}")
    fig = make_subplots(
        rows=2,
        cols=1,
        vertical_spacing=0.02,
        shared_xaxes=True,
    )

    for i, prop in enumerate(df_plot.property_type.unique()):
        df = df_plot[df_plot.property_type == prop]
        # price trend
        fig.add_trace(
            go.Histogram(
                x=df.price,
                name=prop,
                marker_color=PROP_COLOR[prop],
            ),
            row=i + 1,
            col=1,
        )

    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99))
    fig.update_layout(plot_bgcolor=PLOT_BG_COLOR)
    fig.update_layout(title=f"{loc.title()} {year} price distribution")
    # control subplot proportion
    rate_height = 0.5
    gap = 0
    fig.update_layout(
        yaxis=dict(domain=[rate_height + gap, 1]),
        yaxis2=dict(domain=[0, rate_height]),
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_xaxes(title_text="Price", row=2, col=1)
    fig.update_yaxes(fixedrange=True, visible=False)
    fig.update_layout(
        margin=dict(
            t=30,
            r=0,
            b=0,
            l=0,
        ),
    )
    return fig


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", debug=True)

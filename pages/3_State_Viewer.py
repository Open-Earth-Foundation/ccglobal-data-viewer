import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.geoaxes import GeoAxes
from cartopy.io.img_tiles import OSM
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as mplPolygon
from mpl_toolkits.axes_grid1 import AxesGrid
import pandas as pd
import shapely.geometry as geom
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import streamlit as st

from utils import get_state, lat_lon_inside_geom, db_query

with st.sidebar:
    st.header("State Viewer")
    st.write(
        """
        View the location of ClimateTRACE assets within a state.
        Use the controls below to change the figure.
        """
    )
    st.subheader("Select state")
    region_code = st.text_input("State ISO Code:", value="US-CA")
    show_outside_point = st.toggle("Show points outside the region", value=False)
    st.markdown("""---""")

    st.subheader("Background image")
    osm_background = st.toggle("Show background map", value=True)
    map_resolution = st.number_input(
        "Map resolution (higher value, greater resolution)",
        min_value=0,
        max_value=10,
        step=1,
        value=6,
    )
    st.markdown("""---""")

    st.subheader("Figure")
    lat_pad = st.number_input(
        "Latitude padding (degrees)",
        min_value=0.0,
        max_value=90.0,
        step=0.05,
        value=0.1,
    )
    lon_pad = st.number_input(
        "Longitude padding (degrees)",
        min_value=0.0,
        max_value=180.0,
        step=0.05,
        value=0.1,
    )

    st.markdown("""---""")

    st.subheader("Scatter points")
    marker_color = st.text_input("Marker color", value="red")
    marker_size = st.number_input(
        "Marker size", min_value=1, max_value=100, step=5, value=20
    )
    edge_color = st.text_input("Edger color", value="white")
    edge_width = st.number_input(
        "Edge width", min_value=0.0, max_value=1.0, step=0.1, value=0.1
    )

with st.container():
    database_uri = "postgresql://ccglobal:@localhost/ccglobal"
    engine = create_engine(database_uri)
    metadata_obj = MetaData()
    Session = sessionmaker(bind=engine)

    with Session() as session:
        polygon = get_state(region_code)
        west, south, east, north = polygon.bounds

        records = db_query(session, north, south, east, west)

        records_in_geom = [
            record
            for record in records
            if lat_lon_inside_geom(record.lat, record.lon, polygon)
        ]

        if show_outside_point:
            lons = [record.lon for record in records]
            lats = [record.lat for record in records]
        else:
            lons = [record.lon for record in records_in_geom]
            lats = [record.lat for record in records_in_geom]

        reference_numbers = set(
            sorted([record.reference_number for record in records_in_geom])
        )

    imagery = OSM()

    # ==========================
    # Figure
    # ==========================
    facecolor = [0, 0, 0]
    edgecolor = "black"
    alpha = 0.2

    central_longitude = 11
    continent_color = [0.3, 0.3, 0.3]
    coastline_color = [0.25, 0.25, 0.25]
    coastline_width: float = 0.5
    color = marker_color
    marker = "o"
    s = marker_size
    edgecolor = edge_color
    linewidth = edge_width

    fig = plt.figure(dpi=300)

    if osm_background:
        projection = imagery.crs
    else:
        projection = ccrs.Robinson(central_longitude=central_longitude)

    params_axesgrid = {
        "rect": [1, 1, 1],
        "axes_class": (GeoAxes, dict(projection=projection)),
        "share_all": False,
        "nrows_ncols": (1, 1),
        "axes_pad": 0.1,
        "cbar_location": "bottom",
        "cbar_mode": None,
        "cbar_pad": 0.1,
        "cbar_size": "7%",
        "label_mode": "",
    }

    grid = AxesGrid(fig, **params_axesgrid)

    grid[0].scatter(
        lons,
        lats,
        transform=ccrs.PlateCarree(),
        color=color,
        marker=marker,
        zorder=2,
        s=marker_size,
        edgecolor=edgecolor,
        linewidth=linewidth,
    )

    grid[0].set_extent(
        [west - lon_pad, east + lon_pad, south - lat_pad, north + lat_pad],
        crs=ccrs.PlateCarree(),
    )

    polygon_params = {
        "edgecolor": edgecolor,
        "facecolor": facecolor,
        "alpha": alpha,
        "linewidth": 1,
        "transform": ccrs.PlateCarree(),
    }

    try:
        boundary = mplPolygon(polygon.exterior.coords, **polygon_params)
        grid[0].add_patch(boundary)
    except:
        for geom in polygon.geoms:
            boundary = mplPolygon(geom.exterior.coords, **polygon_params)
            grid[0].add_patch(boundary)

    if osm_background:
        grid[0].add_image(imagery, map_resolution)
    else:
        grid[0].add_feature(cfeature.LAND)

    # ==========================
    # Additional information
    # ==========================
    df_tmp = pd.DataFrame(records_in_geom)
    df_locodes = (
        df_tmp.loc[df_tmp[4].notnull(), [4, 3]]
        .drop_duplicates()
        .sort_values(by=[3, 4])
        .reset_index(drop=True)
        .rename(columns={3: "reference_number", 4: "locode"})
    )

    n_cities = len(df_locodes["locode"].drop_duplicates())

    st.header(f"Assets within {region_code}")
    st.write(f"Number of assets: {len(records_in_geom)}")
    st.write(f"Number of cities with data: {n_cities}")
    st.write(f"Reference numbers: {reference_numbers}")
    st.pyplot(fig)

    st.dataframe(df_locodes)

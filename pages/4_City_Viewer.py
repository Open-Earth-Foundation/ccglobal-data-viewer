import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.geoaxes import GeoAxes
from cartopy.io.img_tiles import OSM
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as mplPolygon
from mpl_toolkits.axes_grid1 import AxesGrid
import shapely.geometry as geom
from shapely import wkt
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import streamlit as st

from utils import (
    locode_data,
    lat_lon_inside_geom,
    db_query_climatetrace,
)

with st.sidebar:
    st.header("City Viewer")
    st.write(
        """
        View the location of ClimateTRACE assets within a city.
        Use the controls below to change the figure.
        """
    )
    st.subheader("Select state")
    locode = st.text_input("City LOCODE:", value="US NYC")
    show_outside_point = st.toggle("Show points outside the region", value=False)
    st.markdown("""---""")

    st.subheader("Background image")
    osm_background = st.toggle("Show background map", value=True)
    map_resolution = st.number_input(
        "Map resolution (higher value, greater resolution)",
        min_value=0,
        max_value=10,
        step=1,
        value=10,
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
        records_tmp = locode_data(session, locode)
        records = {
            "geometry": records_tmp[0][0],
            "bbox_north": records_tmp[0][1],
            "bbox_south": records_tmp[0][2],
            "bbox_east": records_tmp[0][3],
            "bbox_west": records_tmp[0][4],
        }

        north = records["bbox_north"] + lat_pad
        south = records["bbox_south"] - lat_pad
        east = records["bbox_east"] + lon_pad
        west = records["bbox_west"] - lon_pad

        results = db_query_climatetrace(session, north, south, east, west)

    imagery = OSM()

    facecolor = [0, 0, 0]
    edgecolor = "black"
    alpha = 0.2

    polygon_wkt = records["geometry"]
    polygon = wkt.loads(polygon_wkt)

    # filter records
    records_in_geom = [
        record
        for record in results
        if lat_lon_inside_geom(record.lat, record.lon, polygon)
    ]

    # plot records
    if show_outside_point:
        lons = [record.lon for record in results]
        lats = [record.lat for record in results]
    else:
        lons = [record.lon for record in records_in_geom]
        lats = [record.lat for record in records_in_geom]

    reference_numbers = set(
        sorted([record.reference_number for record in records_in_geom])
    )

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

    grid[0].set_extent([west, east, south, north], crs=ccrs.PlateCarree())

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

    st.header(f"Assets within {locode}")

    with st.expander("See Figure"):
        st.pyplot(fig)

    st.write(f"Number of assets: {len(records_in_geom)}")
    st.write(f"Reference numbers: {reference_numbers}")
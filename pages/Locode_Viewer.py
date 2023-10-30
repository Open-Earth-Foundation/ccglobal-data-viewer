import cartopy.crs as ccrs
from cartopy.mpl.geoaxes import GeoAxes
from cartopy.io.img_tiles import OSM
import cartopy.feature as cfeature
from matplotlib.patches import Polygon as mplPolygon
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid
from shapely import wkt
import shapely.geometry as geom
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
import streamlit as st


def get_locode_data(session, locode):
    query = text(
        """
        SELECT geometry, bbox_north, bbox_south, bbox_east, bbox_west
        FROM osm
        WHERE locode = :locode
        """
    )
    results = session.execute(query, {'locode': locode}).fetchall()
    if len(results) == 1:
        return dict(results[0])

def locode_data(session, locode):
    query = text(
        """
        SELECT geometry, bbox_north, bbox_south, bbox_east, bbox_west
        FROM osm
        WHERE locode = :locode
        """
    )
    results = session.execute(query, {'locode': locode}).fetchall()
    return results

def data_near_locode(session, north, south, east, west):
    query = text(
           """
           SELECT DISTINCT lat, lon
           FROM asset
           WHERE lat <= :north
           AND lat >= :south
           AND lon <= :east
           AND lon >= :west
           """
    )
    params = {
        'north': north,
        'south': south,
        'east': east,
        'west': west
    }
    return session.execute(query, params).fetchall()

with st.sidebar:
    st.header("ClimateTRACE assets near LOCODE")
    st.write(
        """
        Enter a LOCODE see the location of nearby ClimateTRACE assets.
        """)
    locode = st.text_input("City LOCODE:", value='US NYC')
    osm_background = st.toggle('OSM background image', value=False)
    lat_pad = st.number_input("Latitude padding (degrees)", min_value=0.0, max_value=90.0, step=0.05, value=0.1)
    lon_pad = st.number_input("Longitude padding (degrees)", min_value=0.0, max_value=180.0, step=0.05, value=0.1)

with st.container():
    database_uri = 'postgresql://ccglobal:@localhost/ccglobal'
    engine = create_engine(database_uri)
    metadata_obj = MetaData()
    Session = sessionmaker(bind=engine)

    imagery = OSM()

    facecolor = [0,0,0]
    edgecolor = 'black'
    alpha=0.2

    with Session() as session:
        records_tmp = locode_data(session, locode)
        records = {
            'geometry': records_tmp[0][0],
            'bbox_north': records_tmp[0][1],
            'bbox_south': records_tmp[0][2],
            'bbox_east': records_tmp[0][3],
            'bbox_west': records_tmp[0][4],
        }

    north = records['bbox_north'] + lat_pad
    south = records['bbox_south'] - lat_pad
    east = records['bbox_east'] + lon_pad
    west = records['bbox_west'] - lon_pad

    with Session() as session:
        results = data_near_locode(session, north, south, east, west)

    polygon_wkt = records['geometry']
    polygon = wkt.loads(polygon_wkt)

    central_longitude = 11
    continent_color = [0.3,0.3,0.3]
    coastline_color = [0.25, 0.25, 0.25]
    coastline_width: float = 0.5
    color = 'red'
    marker = 'o'
    s = 20
    edgecolor = 'white'
    linewidth = 0.1

    fig = plt.figure(dpi=300)

    if osm_background:
        projection=imagery.crs
    else:
        projection=ccrs.Robinson(central_longitude=central_longitude)

    params_axesgrid = {
        'rect': [1,1,1],
        'axes_class': (GeoAxes, dict(projection=projection)),
        'share_all': False,
        'nrows_ncols': (1, 1),
        'axes_pad': 0.1,
        'cbar_location': 'bottom',
        'cbar_mode': None,
        'cbar_pad': 0.1,
        'cbar_size': '7%',
        'label_mode': ''
    }

    grid = AxesGrid(fig, **params_axesgrid)

    for result in results:
        lat = result[0]
        lon = result[1]

        grid[0].scatter(
            lon, lat,
            transform=ccrs.PlateCarree(),
            color=color,
            marker=marker,
            zorder=2,
            s=s,
            edgecolor=edgecolor,
            linewidth=linewidth
        )

    grid[0].set_extent([west, east, south, north], crs = ccrs.PlateCarree())

    polygon_params = {
        'edgecolor' : edgecolor,
        'facecolor' : facecolor,
        'alpha' : alpha,
        'linewidth' : 1,
        'transform': ccrs.PlateCarree()
    }

    try:
        boundary = mplPolygon(
            polygon.exterior.coords,
            **polygon_params
        )
        grid[0].add_patch(boundary)
    except:
        for geom in polygon.geoms:
            boundary = mplPolygon(
                geom.exterior.coords,
                **polygon_params
            )
            grid[0].add_patch(boundary)

    if osm_background:
        grid[0].add_image(imagery, 11)
    else:
        grid[0].add_feature(cfeature.LAND)

    st.pyplot(fig)

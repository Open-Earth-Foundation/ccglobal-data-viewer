import cartopy.crs as ccrs
from cartopy.mpl.geoaxes import GeoAxes
from cartopy.io.img_tiles import OSM
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from matplotlib.patches import Polygon as mplPolygon
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid
from shapely import wkt
from shapely.geometry import Point
import shapely.geometry as geom
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
import streamlit as st

def get_country(iso: str):
    shp_countries = shpreader.natural_earth(
        resolution='110m',
        category='cultural',
        name='admin_0_countries'
    )

    for record in shpreader.Reader(shp_countries).records():
        if record.attributes['ISO_A2'].upper() == iso.upper():
            return record.geometry

    return None

def get_state(iso: str):
    shp_states = shpreader.natural_earth(
        resolution='110m',
        category='cultural',
        name='admin_1_states_provinces_lakes'
    )

    for record in shpreader.Reader(shp_states).records():
        if record.attributes['iso_3166_2'].upper() == iso.upper():
            return record.geometry

    return None


def lat_lon_inside_geom(lat, lon, geometry):
    """test if lat lon is inside a WKT geometry

    Parameters
    ----------
    lat: float
        latitude value
    lon: float
        longitude value
    wkt: str
        geometry in well-known-text format

    Returns
    -------
    is_inside: bool
        boolean value indicating whether lat, lon is inside the WKT
    """
    point = Point(lon, lat)
    return point.within(geometry)


def db_query(session, north, south, east, west):
    query = text(
        """
        SELECT DISTINCT lat, lon, filename, reference_number
        FROM asset
        WHERE lat <= :north
        AND lat >= :south
        AND lon <= :east
        AND lon >= :west;
        """
    )
    params = {'north': north , 'south': south, 'east': east, 'west': west}
    result = session.execute(query, params).fetchall()

    return result


with st.sidebar:
    st.header("ClimateTRACE assets within region")
    st.write(
        """
        Enter an ISO region code to see the location of nearby ClimateTRACE assets.
        """)
    region_code = st.text_input("Region ISO Code:", value='US-CA')
    #osm_background = st.toggle('OSM background image', value=False)
    #lat_pad = st.number_input("Latitude padding (degrees)", min_value=0.0, max_value=90.0, step=0.05, value=0.1)
    #lon_pad = st.number_input("Longitude padding (degrees)", min_value=0.0, max_value=180.0, step=0.05, value=0.1)

with st.container():

    database_uri = 'postgresql://ccglobal:@localhost/ccglobal'
    engine = create_engine(database_uri)
    metadata_obj = MetaData()
    Session = sessionmaker(bind=engine)
    session = Session()

    polygon = get_state(region_code)
    west, south, east, north = polygon.bounds

    records = db_query(session, north, south, east, west)

    # filter records
    records_in_geom = [record for record in records if lat_lon_inside_geom(record.lat, record.lon, polygon)]

    # plot records
    lons = [record.lon for record in records_in_geom]
    lats = [record.lat for record in records_in_geom]

    #plt.scatter(lons, lats)

    session.close()



    imagery = OSM()

    osm_background = False

    facecolor = [0,0,0]
    edgecolor = 'black'
    alpha=0.2

    #polygon_wkt = records['geometry']
    #polygon = wkt.loads(polygon_wkt)

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

    grid[0].scatter(
        lons, lats,
        transform=ccrs.PlateCarree(),
        color=color,
        marker=marker,
        zorder=2,
        s=s,
        edgecolor=edgecolor,
        linewidth=linewidth
    )

    padding = 0.1
    grid[0].set_extent([west-padding, east+padding, south-padding, north+padding], crs = ccrs.PlateCarree())

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



    st.pyplot(fig)

    st.write(f"Number of records: {len(records_in_geom)}")
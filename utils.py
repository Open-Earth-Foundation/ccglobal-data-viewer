import cartopy.io.shapereader as shpreader
from shapely.geometry import Point
from sqlalchemy import text


def get_country(iso: str):
    shp_countries = shpreader.natural_earth(
        resolution="110m", category="cultural", name="admin_0_countries"
    )

    for record in shpreader.Reader(shp_countries).records():
        if record.attributes["ISO_A2"].upper() == iso.upper():
            return record.geometry

    return None


def get_state(iso: str):
    shp_states = shpreader.natural_earth(
        resolution="110m", category="cultural", name="admin_1_states_provinces_lakes"
    )

    for record in shpreader.Reader(shp_states).records():
        if record.attributes["iso_3166_2"].upper() == iso.upper():
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
        SELECT DISTINCT lat, lon, filename, reference_number, locode
        FROM asset
        WHERE lat <= :north
        AND lat >= :south
        AND lon <= :east
        AND lon >= :west;
        """
    )
    params = {"north": north, "south": south, "east": east, "west": west}
    result = session.execute(query, params).fetchall()

    return result


def locode_data(session, locode):
    query = text(
        """
        SELECT geometry, bbox_north, bbox_south, bbox_east, bbox_west
        FROM osm
        WHERE locode = :locode
        """
    )
    results = session.execute(query, {"locode": locode}).fetchall()
    return results

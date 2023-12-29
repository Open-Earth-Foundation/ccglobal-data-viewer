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


def db_query_climatetrace(session, north, south, east, west):
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

def db_query_climatetrace_locode(session, locode, sector):
    query = text(
    """
    SELECT DISTINCT locode, EXTRACT(YEAR FROM start_time) AS year, reference_number
    FROM asset
    WHERE locode = :locode
    AND reference_number ILIKE :sector
    """
    )
    params = {"locode": locode, "sector": f'{sector}.%'}
    result = session.execute(query, params).fetchall()

    return result


def db_query_edgar_by_iso(session, iso):
    query = text(
        """
        SELECT DISTINCT cc.locode
        FROM "CityCellOverlapEdgar" AS cc
        JOIN "GridCellEmissionsEdgar" AS gc ON gc.cell_id = cc.cell_id
        WHERE cc.locode LIKE :iso || '%';
        """
    )

    params = {'iso': iso}
    result = session.execute(query, params).fetchall()

    return result

def db_query_city_name(session, city):
    query = text("""
        SELECT locode, name, display_name FROM osm
        WHERE name ILIKE :city;
        """
    )

    params =  {"city": f'%{city}%'}
    result = session.execute(query, params).fetchall()

    return result

def db_query_edgar_by_range(session, north, south, east, west):
    query = text(
        """
        WITH "GridCells" AS (
            SELECT DISTINCT id, lat_center, lon_center
            FROM "GridCellEdgar"
            WHERE lat_center <= :north
            AND lat_center >= :south
            AND lon_center <= :east
            AND lon_center >= :west
        )

        SELECT
            gc.lat_center AS lat,
            gc.lon_center AS lon,
            gce.reference_number,
            cc.locode
        FROM "GridCells" AS gc
        JOIN "CityCellOverlapEdgar" AS cc
            ON gc.id = cc.cell_id
        JOIN "GridCellEmissionsEdgar" AS gce
            ON gc.id = gce.cell_id
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

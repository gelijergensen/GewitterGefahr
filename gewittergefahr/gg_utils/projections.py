"""Methods for handling map projections.

Specifically, this file contains methods for initializing a projection,
converting from lat-long to projection (x-y) coordinates, and converting from
x-y back to lat-long.
"""

from pyproj import Proj
from gewittergefahr.gg_io import myrorss_io

# TODO(thunderhoser): add error-checking to all methods.

EARTH_RADIUS_METRES = 6370997.

# TODO(thunderhoser): put these constants somewhere else.
GRID130_FALSE_EASTING_METRES = 3332090.43552
GRID130_FALSE_NORTHING_METRES = -2279020.17888
GRID236_FALSE_EASTING_METRES = 3332091.40408
GRID236_FALSE_NORTHING_METRES = -2279020.92053
GRID252_FALSE_EASTING_METRES = 3332165.36198
GRID252_FALSE_NORTHING_METRES = -2278963.97252


def init_lambert_conformal_projection(standard_latitudes_deg,
                                      central_longitude_deg):
    """Initializes Lambert conformal projection.

    :param standard_latitudes_deg: length-2 numpy array with standard parallels
        (deg N).  standard_latitudes_deg[0] is the first standard parallel;
        standard_latitudes_deg[1] is the second standard parallel.
    :param central_longitude_deg: central meridian (deg E).
    :return: projection_object: object created by `pyproj.Proj`, specifying the
        Lambert conformal projection.
    """

    return Proj(proj='lcc', lat_1=standard_latitudes_deg[0],
                lat_2=standard_latitudes_deg[1], lon_0=central_longitude_deg,
                rsphere=EARTH_RADIUS_METRES, ellps='sphere')


def project_latlng_to_xy(latitudes_deg, longitudes_deg, projection_object=None,
                         false_easting_metres=None, false_northing_metres=None):
    """Converts from lat-long to projection (x-y) coordinates.

    P = number of points

    :param latitudes_deg: length-P numpy array of latitudes (deg N).
    :param longitudes_deg: length-P numpy array of longitudes (deg E).
    :param projection_object: Projection object created by `pyproj.Proj`.
    :param false_easting_m: False easting.  Will be added to all x-coordinates.
    :param false_northing_m: False northing.  Will be added to all y-
        coordinates.
    :return: x_coords_metres: length-P numpy array of x-coordinates.
    :return: y_coords_metres: length-P numpy array of y-coordinates.
    """

    x_coords_metres, y_coords_metres = projection_object(longitudes_deg,
                                                         latitudes_deg)

    return (x_coords_metres + false_easting_metres,
            y_coords_metres + false_northing_metres)


def project_xy_to_latlng(x_coords_metres, y_coords_metres,
                         projection_object=None, false_easting_metres=None,
                         false_northing_metres=None):
    """Converts from projection (x-y) to lat-long coordinates.

    P = number of points

    :param x_coords_metres: length-P numpy array of x-coordinates.
    :param y_coords_metres: length-P numpy array of y-coordinates.
    :param projection_object: Projection object created by `pyproj.Proj`.
    :param false_easting_metres: False easting.  Will be subtracted from all x-
        coordinates before conversion.
    :param false_northing_metres: False northing.  Will be subtracted from all
        y-coordinates before conversion.
    :return: latitudes_deg: length-P numpy array of latitudes (deg N).
    :return: longitudes_deg: length-P numpy array of longitudes (deg E).
    """

    (longitudes_deg, latitudes_deg) = projection_object(
        x_coords_metres - false_easting_metres,
        y_coords_metres - false_northing_metres, inverse=True)

    return (
        latitudes_deg, myrorss_io.convert_lng_positive_in_west(longitudes_deg))

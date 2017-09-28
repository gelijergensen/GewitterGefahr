"""IO methods for MADIS (Meteorological Assimilation Data Ingest System) data.

DEFINITIONS

MADIS consists of many subdatasets.  We use all subdatasets with near-surface
wind observations, listed below:

- coop stations
- HCN (Historical Climate Network)
- HFMETAR (5-minute meteorological aerodrome reports [METARs])
- maritime observations
- mesonet stations (from several different mesonets, sadly not including the
  Oklahoma Mesonet)
- METAR (hourly, as opposed to 5-minute, METARs)
- NEPP (New England Pilot Project)
- SAO (I have no idea what this stands for, but it contains only Canadian
  stations)
- urbanet stations
"""

import os
import os.path
import numpy
import pandas
from netCDF4 import Dataset
from gewittergefahr.gg_io import downloads
from gewittergefahr.gg_io import raw_wind_io
from gewittergefahr.gg_utils import unzipping
from gewittergefahr.gg_utils import time_conversion
from gewittergefahr.gg_utils import longitude_conversion as lng_conversion
from gewittergefahr.gg_utils import error_checking

# TODO(thunderhoser): replace main method with named method.

DATA_SOURCE = 'madis'
FTP_SERVER_NAME = 'madis-data.ncep.noaa.gov'
FTP_ROOT_DIRECTORY_NAME = 'archive'

ZIPPED_FILE_EXTENSION = '.gz'
UNZIPPED_FILE_EXTENSION = '.netcdf'

# LDAD = Local Data Acquisition and Dissemination system.
LDAD_SUBDATASET_NAMES = ['coop', 'hcn', 'hfmetar', 'mesonet', 'nepp', 'urbanet']
NON_LDAD_SUBDATASET_NAMES = ['maritime', 'metar', 'sao']
SUBDATASET_NAMES = LDAD_SUBDATASET_NAMES + NON_LDAD_SUBDATASET_NAMES

TIME_FORMAT_YEAR = '%Y'
TIME_FORMAT_MONTH = '%m'
TIME_FORMAT_MONTH_YEAR = '%Y%m'
TIME_FORMAT_DAY_OF_MONTH = '%d'
TIME_FORMAT_HOUR = '%Y%m%d_%H00'

LOW_QUALITY_FLAGS = ['X', 'Q', 'k', 'B']
DEFAULT_QUALITY_FLAG = 'y'

WIND_SPEED_FLAG_COLUMN = 'wind_speed_flag'
WIND_DIR_FLAG_COLUMN = 'wind_direction_flag'
WIND_GUST_SPEED_FLAG_COLUMN = 'wind_gust_speed_flag'
WIND_GUST_DIR_FLAG_COLUMN = 'wind_gust_direction_flag'

STATION_ID_COLUMN_ORIG = 'stationId'
STATION_NAME_COLUMN_ORIG = 'stationName'
LATITUDE_COLUMN_ORIG = 'latitude'
LONGITUDE_COLUMN_ORIG = 'longitude'
ELEVATION_COLUMN_ORIG = 'elevation'
WIND_SPEED_COLUMN_ORIG = 'windSpeed'
WIND_DIR_COLUMN_ORIG = 'windDir'
WIND_GUST_SPEED_COLUMN_ORIG = 'windGust'
WIND_GUST_DIR_COLUMN_ORIG = 'windDirMax'
TIME_COLUMN_ORIG = 'observationTime'
TIME_COLUMN_ORIG_BACKUP = 'timeObs'
WIND_SPEED_FLAG_COLUMN_ORIG = 'windSpeedDD'
WIND_DIR_FLAG_COLUMN_ORIG = 'windDirDD'
WIND_GUST_SPEED_FLAG_COLUMN_ORIG = 'windGustDD'
WIND_GUST_DIR_FLAG_COLUMN_ORIG = 'windDirMaxDD'

COLUMN_NAMES = [raw_wind_io.STATION_ID_COLUMN, raw_wind_io.STATION_NAME_COLUMN,
                raw_wind_io.LATITUDE_COLUMN, raw_wind_io.LONGITUDE_COLUMN,
                raw_wind_io.ELEVATION_COLUMN, raw_wind_io.WIND_SPEED_COLUMN,
                raw_wind_io.WIND_DIR_COLUMN, raw_wind_io.WIND_GUST_SPEED_COLUMN,
                raw_wind_io.WIND_GUST_DIR_COLUMN, raw_wind_io.TIME_COLUMN,
                raw_wind_io.TIME_COLUMN, WIND_SPEED_FLAG_COLUMN,
                WIND_DIR_FLAG_COLUMN, WIND_GUST_SPEED_FLAG_COLUMN,
                WIND_GUST_DIR_FLAG_COLUMN]

COLUMN_NAMES_ORIG = [STATION_ID_COLUMN_ORIG, STATION_NAME_COLUMN_ORIG,
                     LATITUDE_COLUMN_ORIG, LONGITUDE_COLUMN_ORIG,
                     ELEVATION_COLUMN_ORIG, WIND_SPEED_COLUMN_ORIG,
                     WIND_DIR_COLUMN_ORIG, WIND_GUST_SPEED_COLUMN_ORIG,
                     WIND_GUST_DIR_COLUMN_ORIG, TIME_COLUMN_ORIG,
                     TIME_COLUMN_ORIG_BACKUP, WIND_SPEED_FLAG_COLUMN_ORIG,
                     WIND_DIR_FLAG_COLUMN_ORIG,
                     WIND_GUST_SPEED_FLAG_COLUMN_ORIG,
                     WIND_GUST_DIR_FLAG_COLUMN_ORIG]

# The following constants are used only in the main method.
NETCDF_FILE_NAME = (
    '/localdata/ryan.lagerquist/aasswp/madis_mesonet_2011-06-08-07.netcdf')
CSV_FILE_NAME = (
    '/localdata/ryan.lagerquist/aasswp/madis_mesonet_winds_2011-06-08-07.csv')


def _column_name_orig_to_new(column_name_orig):
    """Converts column name from orig (MADIS) to new (GewitterGefahr) format.

    :param column_name_orig: Column name in original format.
    :return: column_name: Column name in new format.
    """

    orig_column_flags = [s == column_name_orig for s in COLUMN_NAMES_ORIG]
    orig_column_index = numpy.where(orig_column_flags)[0][0]
    return COLUMN_NAMES[orig_column_index]


def _char_matrix_to_string_list(char_matrix):
    """Converts character matrix to list of strings.

    M = number of strings
    N = max number of characters per string

    :param char_matrix: M-by-N character matrix.
    :return: strings: length-M list of strings.
    """

    num_strings = char_matrix.shape[0]
    strings = [''] * num_strings
    for i in range(num_strings):
        strings[i] = ''.join(char_matrix[i, :]).strip()

    return strings


def _get_ftp_file_name(unix_time_sec, subdataset_name):
    """Generates expected file path on FTP server for given date and subdataset.

    :param unix_time_sec: Time in Unix format.
    :param subdataset_name: Name of subdataset.
    :return: ftp_file_name: Expected file path on FTP server.
    """

    pathless_file_name = _get_pathless_raw_file_name(unix_time_sec, zipped=True)

    if subdataset_name in LDAD_SUBDATASET_NAMES:
        first_subdir_name = 'LDAD'
        second_subdir_name = 'netCDF'
    else:
        first_subdir_name = 'point'
        second_subdir_name = 'netcdf'

    ftp_directory_name = '{0:s}/{1:s}/{2:s}/{3:s}/{4:s}/{5:s}/{6:s}'.format(
        FTP_ROOT_DIRECTORY_NAME,
        time_conversion.unix_sec_to_string(unix_time_sec, TIME_FORMAT_YEAR),
        time_conversion.unix_sec_to_string(unix_time_sec, TIME_FORMAT_MONTH),
        time_conversion.unix_sec_to_string(unix_time_sec,
                                           TIME_FORMAT_DAY_OF_MONTH),
        first_subdir_name, subdataset_name, second_subdir_name)

    return '{0:s}/{1:s}'.format(ftp_directory_name, pathless_file_name)


def _remove_invalid_data(wind_table):
    """Removes rows with invalid wind data.

    "Invalid wind data" means that latitude, longitude, elevation, sustained
    speed, and/or gust speed are out of range.  If either wind direction
    (sustained or gust) is out of range, it will simply be replaced with 0 deg
    (due north), since we don't really care about direction.

    :param wind_table: pandas DataFrame created by read_winds_from_netcdf.
    :return: wind_table: Same as input, except that [1] invalid rows have been
        removed and [2] invalid wind directions have been changed to 0 deg.
    """

    invalid_indices = raw_wind_io.check_latitudes(
        wind_table[raw_wind_io.LATITUDE_COLUMN].values)
    wind_table.drop(wind_table.index[invalid_indices], axis=0, inplace=True)

    invalid_indices = raw_wind_io.check_longitudes(
        wind_table[raw_wind_io.LONGITUDE_COLUMN].values)
    wind_table.drop(wind_table.index[invalid_indices], axis=0, inplace=True)

    invalid_indices = raw_wind_io.check_elevations(
        wind_table[raw_wind_io.ELEVATION_COLUMN].values)
    wind_table.drop(wind_table.index[invalid_indices], axis=0, inplace=True)

    invalid_sustained_indices = raw_wind_io.check_wind_speeds(
        wind_table[raw_wind_io.WIND_SPEED_COLUMN].values)
    wind_table[raw_wind_io.WIND_SPEED_COLUMN].values[
        invalid_sustained_indices] = numpy.nan

    invalid_gust_indices = raw_wind_io.check_wind_speeds(
        wind_table[raw_wind_io.WIND_GUST_SPEED_COLUMN].values)
    wind_table[raw_wind_io.WIND_GUST_SPEED_COLUMN].values[
        invalid_gust_indices] = numpy.nan

    invalid_indices = list(
        set(invalid_gust_indices).intersection(invalid_sustained_indices))
    wind_table.drop(wind_table.index[invalid_indices], axis=0, inplace=True)

    invalid_indices = raw_wind_io.check_wind_directions(
        wind_table[raw_wind_io.WIND_DIR_COLUMN].values)
    wind_table[raw_wind_io.WIND_DIR_COLUMN].values[
        invalid_indices] = raw_wind_io.WIND_DIR_DEFAULT_DEG

    invalid_indices = raw_wind_io.check_wind_directions(
        wind_table[raw_wind_io.WIND_GUST_DIR_COLUMN].values)
    wind_table[raw_wind_io.WIND_GUST_DIR_COLUMN].values[
        invalid_indices] = raw_wind_io.WIND_DIR_DEFAULT_DEG

    wind_table[raw_wind_io.LONGITUDE_COLUMN] = (
        lng_conversion.convert_lng_positive_in_west(
            wind_table[raw_wind_io.LONGITUDE_COLUMN].values, allow_nan=False))
    return wind_table


def _remove_low_quality_data(wind_table):
    """Removes low-quality wind data.

    Low-quality wind speeds will be changed to NaN, and low-quality wind
    directions will be changed to 0 deg N.  Any row left with only low-quality
    wind speeds will be removed.

    :param wind_table: pandas DataFrame created by read_winds_from_netcdf.
    :return: wind_table: Same as input, with 4 exceptions.  [1] Low-quality wind
        speeds are NaN; [2] low-quality wind directions are 0 deg N; [3] rows
        with only low-quality wind speeds have been removed; [4] quality flags
        have been removed.
    """

    is_low_quality = [f in LOW_QUALITY_FLAGS for f in
                      wind_table[WIND_SPEED_FLAG_COLUMN].values]
    low_quality_indices = numpy.where(is_low_quality)[0]
    wind_table[raw_wind_io.WIND_SPEED_COLUMN].values[
        low_quality_indices] = numpy.nan

    is_low_quality = [f in LOW_QUALITY_FLAGS for f in
                      wind_table[WIND_DIR_FLAG_COLUMN].values]
    low_quality_indices = numpy.where(is_low_quality)[0]
    wind_table[raw_wind_io.WIND_DIR_COLUMN].values[
        low_quality_indices] = raw_wind_io.WIND_DIR_DEFAULT_DEG

    is_low_quality = [f in LOW_QUALITY_FLAGS for f in
                      wind_table[WIND_GUST_SPEED_FLAG_COLUMN].values]
    low_quality_indices = numpy.where(is_low_quality)[0]
    wind_table[raw_wind_io.WIND_GUST_SPEED_COLUMN].values[
        low_quality_indices] = numpy.nan

    is_low_quality = [f in LOW_QUALITY_FLAGS for f in
                      wind_table[WIND_GUST_DIR_FLAG_COLUMN].values]
    low_quality_indices = numpy.where(is_low_quality)[0]
    wind_table[raw_wind_io.WIND_GUST_DIR_COLUMN].values[
        low_quality_indices] = raw_wind_io.WIND_DIR_DEFAULT_DEG

    columns_to_drop = [WIND_SPEED_FLAG_COLUMN, WIND_DIR_FLAG_COLUMN,
                       WIND_GUST_SPEED_FLAG_COLUMN, WIND_GUST_DIR_FLAG_COLUMN]
    wind_table.drop(columns_to_drop, axis=1, inplace=True)

    return wind_table.loc[
        wind_table[[raw_wind_io.WIND_SPEED_COLUMN,
                    raw_wind_io.WIND_GUST_SPEED_COLUMN]].notnull().any(
                        axis=1)]


def _get_pathless_raw_file_name(unix_time_sec, zipped=True):
    """Generates pathless name for raw MADIS file.

    :param unix_time_sec: Time in Unix format.
    :param zipped: Boolean flag.  If True, will generate name for zipped file.
        If False, will generate name for unzipped file.
    :return: pathless_raw_file_name: Pathless name for raw MADIS file.
    """

    if zipped:
        return '{0:s}{1:s}'.format(
            time_conversion.unix_sec_to_string(unix_time_sec, TIME_FORMAT_HOUR),
            ZIPPED_FILE_EXTENSION)

    return '{0:s}{1:s}'.format(
        time_conversion.unix_sec_to_string(unix_time_sec, TIME_FORMAT_HOUR),
        UNZIPPED_FILE_EXTENSION)


def extract_netcdf_from_gzip(unix_time_sec=None, subdataset_name=None,
                             top_raw_directory_name=None):
    """Extracts NetCDF file from gzip archive.

    Keep in mind that all gzip archive contain only one file.

    :param unix_time_sec: Time in Unix format.
    :param subdataset_name: Name of subdataset.
    :param top_raw_directory_name: Top-level directory with raw MADIS files.
    :return: netcdf_file_name: Path to output file.
    """

    gzip_file_name = find_local_raw_file(
        unix_time_sec=unix_time_sec, subdataset_name=subdataset_name,
        top_local_directory_name=top_raw_directory_name, zipped=True,
        raise_error_if_missing=True)

    netcdf_file_name = find_local_raw_file(
        unix_time_sec=unix_time_sec, subdataset_name=subdataset_name,
        top_local_directory_name=top_raw_directory_name, zipped=False,
        raise_error_if_missing=False)

    unzipping.unzip_gzip(gzip_file_name, netcdf_file_name)
    return netcdf_file_name


def find_local_raw_file(unix_time_sec=None, subdataset_name=None,
                        top_local_directory_name=None, zipped=True,
                        raise_error_if_missing=True):
    """Finds raw file on local machine.

    This file should contain all data for one subdataset and hour.

    :param unix_time_sec: Time in Unix format.
    :param subdataset_name: Name of subdataset.
    :param top_local_directory_name: Top-level directory with raw MADIS files.
    :param zipped: Boolean flag.  If True, will look for zipped file.  If False,
        will look for unzipped file.
    :param raise_error_if_missing: Boolean flag.  If True and file is missing,
        this method will raise an error.
    :return: raw_file_name: File path.  If raise_error_if_missing = False and
        file is missing, this will be the *expected* path.
    :raises: ValueError: if raise_error_if_missing = True and file is missing.
    """

    error_checking.assert_is_string(subdataset_name)
    error_checking.assert_is_string(top_local_directory_name)
    error_checking.assert_is_boolean(zipped)
    error_checking.assert_is_boolean(raise_error_if_missing)

    pathless_file_name = _get_pathless_raw_file_name(unix_time_sec,
                                                     zipped=zipped)

    raw_file_name = '{0:s}/{1:s}/{2:s}/{3:s}'.format(
        top_local_directory_name, subdataset_name,
        time_conversion.unix_sec_to_string(unix_time_sec,
                                           TIME_FORMAT_MONTH_YEAR),
        pathless_file_name)

    if raise_error_if_missing and not os.path.isfile(raw_file_name):
        raise ValueError(
            'Cannot find raw file.  Expected at location: ' + raw_file_name)

    return raw_file_name


def download_gzip_from_ftp(unix_time_sec=None, subdataset_name=None,
                           top_local_directory_name=None, ftp_user_name=None,
                           ftp_password=None, raise_error_if_fails=True):
    """Downloads gzip file from FTP server.

    The gzip file should contain a single NetCDF file, containing all data for
    one subdataset and one hour.

    :param unix_time_sec: Time in Unix format.
    :param subdataset_name: Name of subdataset.
    :param top_local_directory_name: Path to top-level directory for raw MADIS
        files.
    :param ftp_user_name: Username on FTP server.  If you want to login
        anonymously, leave this as None.
    :param ftp_password: Password on FTP server.  If you want to login
        anonymously, leave this as None.
    :param raise_error_if_fails: Boolean flag.  If True and download fails, will
        raise error.
    :return: local_gzip_file_name: Path to file on local machine.  If download
        failed but raise_error_if_fails = False, this will be None.
    """

    error_checking.assert_is_string(subdataset_name)
    ftp_file_name = _get_ftp_file_name(unix_time_sec, subdataset_name)

    local_gzip_file_name = find_local_raw_file(
        unix_time_sec=unix_time_sec, subdataset_name=subdataset_name,
        top_local_directory_name=top_local_directory_name, zipped=True,
        raise_error_if_missing=False)

    return downloads.download_file_from_ftp(
        server_name=FTP_SERVER_NAME, user_name=ftp_user_name,
        password=ftp_password, ftp_file_name=ftp_file_name,
        local_file_name=local_gzip_file_name,
        raise_error_if_fails=raise_error_if_fails)


def download_netcdf_from_ftp(unix_time_sec=None, subdataset_name=None,
                             top_local_directory_name=None, ftp_user_name=None,
                             ftp_password=None, raise_error_if_fails=True):
    """Downloads NetCDF file from FTP server.

    The only difference between this method and download_gzip_from_ftp is that
    this method unzips the gzip file.

    :param unix_time_sec: See documentation for download_gzip_from_ftp.
    :param subdataset_name: See documentation for download_gzip_from_ftp.
    :param top_local_directory_name: See documentation for
        download_gzip_from_ftp.
    :param ftp_user_name: See documentation for download_gzip_from_ftp.
    :param ftp_password: See documentation for download_gzip_from_ftp.
    :param raise_error_if_fails: See documentation for download_gzip_from_ftp.
    :return: local_netcdf_file_name: Path to file on local machine.  If download
        failed but raise_error_if_fails = False, this will be None.
    """

    local_gzip_file_name = download_gzip_from_ftp(
        unix_time_sec=unix_time_sec, subdataset_name=subdataset_name,
        top_local_directory_name=top_local_directory_name,
        ftp_user_name=ftp_user_name, ftp_password=ftp_password,
        raise_error_if_fails=raise_error_if_fails)

    if local_gzip_file_name is None:
        return None

    return extract_netcdf_from_gzip(
        unix_time_sec=unix_time_sec, subdataset_name=subdataset_name,
        top_raw_directory_name=top_local_directory_name)


def read_winds_from_netcdf(netcdf_file_name):
    """Reads wind data from NetCDF file.

    :param netcdf_file_name: Path to input file.
    :return: wind_table: pandas DataFrame with the following columns.
    wind_table.station_id: String ID for station.
    wind_table.station_name: Verbose name for station.
    wind_table.latitude_deg: Latitude (deg N).
    wind_table.longitude_deg: Longitude (deg E).
    wind_table.elevation_m_asl: Elevation (metres above sea level).
    wind_table.unix_time_sec: Observation time (seconds since 0000 UTC 1 Jan
        1970).
    wind_table.wind_speed_m_s01: Speed of sustained wind (m/s).
    wind_table.wind_direction_deg: Direction of sustained wind (degrees of
        origin -- i.e., direction that the wind is coming from -- as per
        meteorological convention).
    wind_table.wind_gust_speed_m_s01: Speed of wind gust (m/s).
    wind_table.wind_gust_direction_deg: Direction of wind gust (degrees of
        origin).
    """

    error_checking.assert_file_exists(netcdf_file_name)
    netcdf_dataset = Dataset(netcdf_file_name)
    station_names = _char_matrix_to_string_list(
        netcdf_dataset.variables[STATION_NAME_COLUMN_ORIG][:])

    try:
        station_ids = _char_matrix_to_string_list(
            netcdf_dataset.variables[STATION_ID_COLUMN_ORIG][:])
    except KeyError:
        station_ids = station_names

    for i in range(len(station_ids)):
        station_ids[i] = raw_wind_io.append_source_to_station_id(station_ids[i],
                                                                 DATA_SOURCE)

    try:
        unix_times_sec = netcdf_dataset.variables[TIME_COLUMN_ORIG][:]
    except KeyError:
        unix_times_sec = netcdf_dataset.variables[TIME_COLUMN_ORIG_BACKUP][:]

    wind_speeds_m_s01 = netcdf_dataset.variables[WIND_SPEED_COLUMN_ORIG][:]
    wind_speed_quality_flags = netcdf_dataset.variables[
        WIND_SPEED_FLAG_COLUMN_ORIG][:]
    num_observations = len(wind_speeds_m_s01)

    try:
        wind_directions_deg = netcdf_dataset.variables[WIND_DIR_COLUMN_ORIG][:]
        wind_dir_quality_flags = netcdf_dataset.variables[
            WIND_DIR_FLAG_COLUMN_ORIG][:]
    except KeyError:
        wind_directions_deg = numpy.full(num_observations,
                                         raw_wind_io.WIND_DIR_DEFAULT_DEG)
        wind_dir_quality_flags = [DEFAULT_QUALITY_FLAG] * num_observations

    try:
        wind_gust_speeds_m_s01 = netcdf_dataset.variables[
            WIND_GUST_SPEED_COLUMN_ORIG][:]
        wind_gust_speed_quality_flags = netcdf_dataset.variables[
            WIND_GUST_SPEED_FLAG_COLUMN_ORIG][:]
    except KeyError:
        wind_gust_speeds_m_s01 = numpy.full(num_observations, numpy.nan)
        wind_gust_speed_quality_flags = (
            [DEFAULT_QUALITY_FLAG] * num_observations)

    try:
        wind_gust_directions_deg = netcdf_dataset.variables[
            WIND_GUST_DIR_COLUMN_ORIG][:]
        wind_gust_dir_quality_flags = netcdf_dataset.variables[
            WIND_GUST_DIR_FLAG_COLUMN_ORIG][:]
    except KeyError:
        wind_gust_directions_deg = numpy.full(num_observations,
                                              raw_wind_io.WIND_DIR_DEFAULT_DEG)
        wind_gust_dir_quality_flags = [DEFAULT_QUALITY_FLAG] * num_observations

    wind_dict = {raw_wind_io.STATION_ID_COLUMN: station_ids,
                 raw_wind_io.STATION_NAME_COLUMN: station_names,
                 raw_wind_io.LATITUDE_COLUMN: netcdf_dataset.variables[
                     LATITUDE_COLUMN_ORIG][:],
                 raw_wind_io.LONGITUDE_COLUMN: netcdf_dataset.variables[
                     LONGITUDE_COLUMN_ORIG][:],
                 raw_wind_io.ELEVATION_COLUMN: netcdf_dataset.variables[
                     ELEVATION_COLUMN_ORIG][:],
                 raw_wind_io.TIME_COLUMN: numpy.array(unix_times_sec).astype(
                     int),
                 raw_wind_io.WIND_SPEED_COLUMN: wind_speeds_m_s01,
                 raw_wind_io.WIND_DIR_COLUMN: wind_directions_deg,
                 raw_wind_io.WIND_GUST_SPEED_COLUMN: wind_gust_speeds_m_s01,
                 raw_wind_io.WIND_GUST_DIR_COLUMN: wind_gust_directions_deg,
                 WIND_SPEED_FLAG_COLUMN: wind_speed_quality_flags,
                 WIND_DIR_FLAG_COLUMN: wind_dir_quality_flags,
                 WIND_GUST_SPEED_FLAG_COLUMN: wind_gust_speed_quality_flags,
                 WIND_GUST_DIR_FLAG_COLUMN: wind_gust_dir_quality_flags}

    wind_table = pandas.DataFrame.from_dict(wind_dict)
    wind_table = _remove_invalid_data(wind_table)
    return _remove_low_quality_data(wind_table)


if __name__ == '__main__':
    WIND_TABLE = read_winds_from_netcdf(NETCDF_FILE_NAME)
    print WIND_TABLE

    WIND_TABLE = raw_wind_io.sustained_and_gust_to_uv_max(WIND_TABLE)
    print WIND_TABLE

    raw_wind_io.write_winds_to_csv(WIND_TABLE, CSV_FILE_NAME)

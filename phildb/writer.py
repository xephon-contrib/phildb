import calendar
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import numpy as np
import os
import pandas as pd
from struct import pack, unpack, calcsize

import logging
logger = logging.getLogger(__name__)

from phildb.constants import DEFAULT_META_ID, MISSING_VALUE, METADATA_MISSING_VALUE
from phildb.log_handler import LogHandler
from phildb.exceptions import DataError
from phildb.reader import __read, read

field_names = ['date', 'value', 'metaID']
entry_format = 'ldi' # long, double, int; See field names above.
entry_size = calcsize(entry_format)

def __pack(record_date, value, default_flag=DEFAULT_META_ID):

    if np.isnan(value):
        data = pack(entry_format,
                    record_date,
                    MISSING_VALUE,
                    METADATA_MISSING_VALUE)
    else:
        data = pack(entry_format, record_date, value, default_flag)

    return data

def __convert_and_validate(ts, freq):
    """
        Enforces frequency.

        :param ts: Pandas Series object
        :type ts: pandas.Series
    """

    if freq == 'IRR':
        series = ts
    else:
        series = ts.asfreq(freq)

    return series


def write(tsdb_file, ts, freq):
    """
        Smart write.

        Will only update existing values where they have changed.
        Changed existing values are returned in a list.

        :param tsdb_file: File to write timeseries data into.
        :type tsdb_file: string
        :param ts: Timeseries data to write.
        :type ts: pd.Series
        :param freq: Frequency of the data. (e.g. 'D' for daily, '1Min' for minutely).
            Accepts any string that pandas.TimeSeries.asfreq does or 'IRR' for irregular data.
        :type freq: string
    """

    series = __convert_and_validate(ts, freq)

    log_entries = {'C': [], 'U': []}

    if len(series) == 0:
        return log_entries

    # If the file didn't exist it is a straight foward write and we can
    # just return at the end of this if block.
    if not os.path.isfile(tsdb_file):
        with open(tsdb_file, 'wb') as writer:
            for date, value in zip(series.index, series.values):
                datestamp = calendar.timegm(date.utctimetuple())
                log_entries['C'].append(
                    (
                        datestamp,
                        value,
                        DEFAULT_META_ID
                    )
                )
                data = __pack(datestamp, value)
                writer.write(data)

        return log_entries

    # If we reached here it wasn't a straight write to a new file.
    if freq == 'IRR':
        return write_irregular_data(tsdb_file, series)
    else:
        return write_regular_data(tsdb_file, series)

def write_regular_data(tsdb_file, series):
    """
        Smart write. Expects continuous time series.

        Will only update existing values where they have changed.
        Changed existing values are returned in a list.

        :param tsdb_file: File to write timeseries data into.
        :type tsdb_file: string
        :param series: Pandas Series of regular data to write.
        :type series: pandas.Series
    """
    start_date = series.index[0]
    end_date = series.index[-1]

    log_entries = {'C': [], 'U': []}
    with open(tsdb_file, 'rb') as reader:
        first_record = unpack(entry_format, reader.read(entry_size))
        reader.seek(entry_size * -1, os.SEEK_END)
        last_record = unpack(entry_format, reader.read(entry_size))

    first_record_date = dt.utcfromtimestamp(first_record[0])
    last_record_date = dt.utcfromtimestamp(last_record[0])

    freqstr = series.index.freqstr

    if freqstr[-1] == 'T':
        if len(freqstr) == 1:
            freq_mult = 1
        else:
            freq_mult = int(freqstr[:-1])
        freqstr = 'T'
    else:
        freq_mult = 1

    if freqstr[-1] == 'S' and len(freqstr) > 1:
        freqstr = freqstr[:-1]

    offset = start_date.to_period(freqstr) - pd.to_datetime(first_record_date).to_period(freqstr)

    # We are updating existing data
    if start_date <= last_record_date:
        with open(tsdb_file, 'r+b') as writer:
            existing_records = []

            # Read existing overlapping data for comparisons
            writer.seek(entry_size * offset, os.SEEK_SET)

            for record in iter(lambda: writer.read(entry_size), ""):
                if not record: break
                existing_records.append(unpack(entry_format, record))

            records_length = len(existing_records)

            # Start a count for records from the starting write position
            rec_count = 0
            writer.seek(entry_size * offset, os.SEEK_SET)
            for date, value in zip(series.index, series.values):
                datestamp = calendar.timegm(date.utctimetuple())
                overlapping = rec_count <= records_length - 1

                if overlapping and (existing_records[rec_count][1] == value or existing_records[rec_count][2] == MISSING_VALUE):
                    # Skip writing the entry if it hasn't changed.
                    writer.seek(entry_size * (rec_count +1) + (entry_size * offset), os.SEEK_SET)
                elif overlapping and existing_records[rec_count][1] != value:
                    log_entries['U'].append(existing_records[rec_count])

                    log_entries['C'].append(
                        (
                            datestamp,
                            value,
                            DEFAULT_META_ID
                        )
                    )
                    data = __pack(datestamp, value)
                    writer.write(data)
                else:
                    data = __pack(datestamp, value)
                    log_entries['C'].append(
                        (
                            datestamp,
                            value,
                            DEFAULT_META_ID
                        )
                    )
                    writer.write(data)
                rec_count += 1

    # We are appending data
    elif start_date > last_record_date:
        with open(tsdb_file, 'a+b') as writer:
            last_record_date = pd.Timestamp(last_record_date, offset=series.index.freq) + 1

            missing_dates = pd.date_range(last_record_date, start_date - 1, freq = series.index.freq)
            for the_date in missing_dates:
                datestamp = calendar.timegm(the_date.utctimetuple())
                log_entries['C'].append(
                    (
                        datestamp,
                        MISSING_VALUE,
                        METADATA_MISSING_VALUE
                    )
                )

                data = pack(
                    entry_format,
                    datestamp,
                    MISSING_VALUE,
                    METADATA_MISSING_VALUE
                )

                writer.write(data)

            for date, value in zip(series.index, series.values):
                datestamp = calendar.timegm(date.utctimetuple())
                log_entries['C'].append(
                    (
                        datestamp,
                        value,
                        DEFAULT_META_ID
                    )
                )
                data = __pack(datestamp, value)
                writer.write(data)

    else: # Not yet supported
        raise NotImplementedError

    return log_entries

def write_irregular_data(tsdb_file, series):
    """
        Smart write of irregular data.

        Will only update existing values where they have changed.
        Changed existing values are returned in a list.

        :param tsdb_file: File to write timeseries data into.
        :type tsdb_file: string
        :param series: Pandas Series of irregular data to write.
        :type series: pandas.Series
        :type freq: string
    """
    existing = __read(tsdb_file)

    overlap_idx = existing.index.intersection(series.index)
    modified = series.ix[overlap_idx] != existing.value.ix[overlap_idx]
    records_to_modify = existing.loc[overlap_idx].ix[modified.values]
    new_records = series.index.difference(existing.index)

    log_entries = {'C': [], 'U': []}

    if len(records_to_modify) == 0 and len(new_records) == 0:
        return log_entries

    for date, orig_value, meta_id, new_value in zip(
        records_to_modify.index,
        records_to_modify.value,
        records_to_modify.metaID,
        series.loc[records_to_modify.index]
    ):
        datestamp = int(date.value / 1000000000)
        log_entries['C'].append((datestamp, new_value, meta_id))
        log_entries['U'].append((datestamp, orig_value, meta_id))

    append_only = len(overlap_idx) == 0
    if append_only:
        merged = series
        fmode = 'ab'
    else:
        # combine_first does not preserve null values in the original series.
        # So do an initial merge.
        merged = series.combine_first(existing.value)
        fmode = 'wb'

    # Then replace the null values from the update series.
    null_vals = series.isnull()
    null_idx = null_vals.loc[null_vals==True].index
    merged.loc[null_idx] = np.nan

    merged = pd.DataFrame({'value': merged})

    merged['datestamp'] = pd.Series(merged.index.map(
                               lambda dateval: dateval.value // 1000000000,
                           ), index=merged.index)

    new_logs = [(row.datestamp, row.value, DEFAULT_META_ID)
                for idx, row in merged.ix[new_records].iterrows()]
    log_entries['C'] += new_logs

    os.rename(tsdb_file, tsdb_file + 'backup')

    try:
        with open(tsdb_file, fmode) as writer:
            def write_record(row):
                writer.write(__pack(int(row[0]), row[1]))
                return row
            np.apply_along_axis(write_record, 1, merged[['datestamp', 'value']].values)
    except Exception:
        # On any failure writing restore the original file.
        os.rename(tsdb_file + 'backup', tsdb_file)
        logger.exception("Error writing irregular data to %s. No data change made.", tsdb_file)
        raise
    else:
        # On successfull write remove the original file.
        os.unlink(tsdb_file + 'backup')


    return log_entries

def write_log(log_file, modified, replacement_datetime):

    if not os.path.exists(log_file):
        with LogHandler(log_file, 'w') as writer:
            writer.create_skeleton()

    with LogHandler(log_file, 'a') as writer:
        writer.write(modified, calendar.timegm(replacement_datetime.utctimetuple()))

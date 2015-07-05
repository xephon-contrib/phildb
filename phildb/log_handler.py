import numpy as np
import tables
from phildb.constants import MISSING_VALUE, METADATA_MISSING_VALUE

class TabDesc(tables.IsDescription):
    time = tables.Int32Col(dflt=0, pos=0)
    value = tables.Float64Col(dflt=np.nan, pos=1)
    meta = tables.Int32Col(dflt=0, pos=2)
    replacement_time = tables.Int32Col(dflt=0, pos=3)

class LogHandler:
    """
    """

    FILTERS = tables.Filters(complib='zlib', complevel=9)

    def __init__(self, filename, mode):
        self.hdf5 = tables.open_file(filename, mode, filters=self.FILTERS)

    def create_skeleton(self):
        """
            Create the skeleton of the log self.hdf5.
        """
        data_group = self.hdf5.create_group('/', 'data', 'data group')

        try:
            new_table = self.hdf5.create_table(data_group,
                     'log',
                     TabDesc
                )
        except tables.exceptions.NodeError as e:
            pass

        self.hdf5.flush()

    def write(self, log_entries, operation_datetime):

        ts_table = self.hdf5.get_node('/data/log')

        index_row = ts_table.row
        for dt, val, meta in iter(log_entries['C']):
            if val is np.nan:
                val = MISSING_VALUE
                meta = METADATA_MISSING_VALUE

            index_row["time"] = dt
            index_row["value"] = val
            index_row["meta"] = meta
            index_row["replacement_time"] = operation_datetime
            index_row.append()

        self.hdf5.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__del__()

    def __del__(self):
        if self.hdf5 is not None:
            self.hdf5.close()
            self.hdf5 = None

    def __str__(self):
        return str(self.hdf5)

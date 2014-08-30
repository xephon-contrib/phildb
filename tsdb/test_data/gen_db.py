import os
import shutil
import sys
import datetime
import pandas
from tsdb.database import TSDB
from tsdb.create import create

test_tsdb_path = os.path.join(os.path.dirname(__file__), 'test_tsdb')

try:
    shutil.rmtree(test_tsdb_path)
except OSError as e:
    if e.errno != 2: # Code 2: No such file or directory.
        raise

create(test_tsdb_path)
db = TSDB(test_tsdb_path)

db.add_measurand('Q', 'STREAMFLOW', 'Streamflow')
db.add_source('DATA_SOURCE', '')

db.add_timeseries('410730')
db.add_timeseries_instance('410730', 'Q', 'DATA_SOURCE', 'D', '')
db.write('410730', 'Q', [[datetime.date(2014, 1, 1),
            datetime.date(2014, 1, 2),
            datetime.date(2014, 1, 3)],
            [1,2,3]],
            'DATA_SOURCE',
            'D'
        )

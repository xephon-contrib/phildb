import argparse

# Disable unused import warnings, because we want these imported
# not for immediate use but for interactive use once the console
# is loaded.
from datetime import datetime, date # pylint:disable=unused-import
import numpy as np # pylint:disable=unused-import
import pandas as pd # pylint:disable=unused-import
from matplotlib import pyplot as plt # pylint:disable=unused-import

from IPython.terminal.embed import InteractiveShellEmbed

from phildb import __version__
from phildb.database import PhilDB

def main():
    ipshell = InteractiveShellEmbed()

    parser = argparse.ArgumentParser(description='Open PhilDB database.')
    parser.add_argument('dbname', help="PhilDB database to open", nargs='?')
    parser.add_argument('--version', action='store_true', help="Print version and exit.")

    args = parser.parse_args()

    if args.version:
        print("PhilDB version: {0}".format(__version__))
        exit()

    if args.dbname is None:
        print(parser.print_help())
        exit()

    db = PhilDB(args.dbname)
    ipshell("Running timeseries database: {0}\n"
            "Access the 'db' object to operate on the database.\n"
            "\n"
            "Run db.help() for a list of available commands.".format(db))

if __name__ == "__main__":
    main()

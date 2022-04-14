import os
from os.path import dirname, abspath, join
from dotenv import load_dotenv

load_dotenv()
# /src
SRC = dirname(abspath(__file__))

# path to Australia dataset
AUS_PATH = os.environ.get("AUS_DATA_ROOT")
# path to PriceFinder data dir
PRICEFINDER_PATH = os.environ.get("PRICEFINDER_DATA_ROOT")
if not AUS_PATH or not PRICEFINDER_PATH:
    raise ValueError('.env empty or not found, please insert AUS_ROOT and PRICEFINDER_ROOT in src/.env')

# path to locality boundary data
LOC_BOUND_PATH = join(AUS_PATH, os.environ.get("LOC_BOUND_NAME"))
# path to PriceFinder sql db
PF_DB_PATH = join(PRICEFINDER_PATH, os.environ.get("PF_DB_NAME"))
# path to suburb coordinates json
SUBURB_COORD_PATH = join(AUS_PATH, os.environ.get('SUBURB_COORD_NAME'))


def main():
    print(SRC)
    print(AUS_PATH)
    print(LOC_BOUND_PATH)
    print(PRICEFINDER_PATH)
    print(PF_DB_PATH)


if __name__ == "__main__":
    main()

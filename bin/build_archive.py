from typing import Tuple

import dask.array
import numpy as np
import pandas as pd
import xarray as xr
from gcsfs import GCSFileSystem
from loguru import logger


def build_chirps_archive(
    demo_path: str,
    start_date: str,
    end_date: str,
    chunks: Tuple[int, int, int],
    storage_root: str,
) -> int:

    mapper = GCSFileSystem().get_mapper

    dt_range = pd.date_range(start_date, end=end_date, freq="D")

    demo_ds = xr.open_dataset(demo_path)

    # first, build the coordinates
    coords = {
        "latitude": demo_ds.latitude.data,
        "longitude": demo_ds.longitude.data,
        "time": dt_range,
    }

    # next, build the variables
    # use a dask array hold the dummy dimensions
    dummies = dask.array.zeros(
        (demo_ds.latitude.shape[0], demo_ds.longitude.shape[0], dt_range.shape[0]),
        chunks=chunks,
        dtype=np.float32,
    )

    # mock-up the dataset
    ds = xr.Dataset({"precip": (tuple(coords.keys()), dummies)}, coords=coords)

    # Now we write the metadata without computing any array values
    ds.to_zarr(mapper(storage_root), compute=False, consolidated=True)

    return 1


if __name__ == "__main__":

    logger.info("building chirps archive")

    build_chirps_archive(
        demo_path="/path/to/my-demo.nc",
        start_date="1981-01-01 00:00:00",
        end_date="2024-12-31 23:00:00",
        chunks=(100, 100, 1461),  # lat, lon, day
        storage_root="<my-storage-root>",
    )

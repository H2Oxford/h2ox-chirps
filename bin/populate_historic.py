import multiprocessing as mp
import os
import pickle
from datetime import datetime
from typing import List, Union

import pandas as pd
import xarray as xr
import zarr
from gcsfs import GCSFileSystem
from loguru import logger
from tqdm import tqdm

from h2ox.chirps.utils import download_blob_to_filename


def populate_historic_single(
    zero_dt: str,
    archive_path: str,
    dataset_path: str,
    slices: Union[str, list],
):
    zero_dt = datetime.strptime(zero_dt, "%Y-%m-%d")

    mapper = GCSFileSystem().get_mapper
    z = zarr.open(mapper(archive_path), "r+")["precip"]

    ds = xr.open_dataset(dataset_path)

    time_idx_ini = (pd.to_datetime(ds.time.data.min()) - zero_dt).days

    logger.info(f"time_idx={time_idx_ini}")

    time_slice = slice(time_idx_ini, time_idx_ini + ds.time.shape[0])

    if isinstance(slices, str):
        slices = pickle.load(open(slices, "rb"))

    for s in tqdm(slices, total=len(slices), desc=os.path.split(dataset_path)[-1]):

        arr = (
            ds["precip"]
            .transpose("latitude", "longitude", "time")[s[0], s[1], :]
            .compute()
            .data
        )

        z[s[0], s[1], time_slice] = arr

    return 1


def populate_historic_loop(
    multi: bool,
    path_template: str,
    year_range: List[int],
    path_root: str,
    slices_path: str,
):
    if multi:
        pool = mp.Pool(4)

    slices = pickle.load(open(slices_path, "rb"))

    for year in year_range:

        logger.info(f"Doing {year}")

        # download
        remote_path = path_template.replace("YEAR", str(year))
        fname = os.path.join(path_root, os.path.split(remote_path)[-1])

        download_blob_to_filename(remote_path, fname)

        logger.info(f"Downloaded {year}")

        if multi:
            chunk_size = len(slices) // 4 + 1
            slice_chunks = [
                slices[ii * chunk_size : (ii + 1) * chunk_size] for ii in range(4)
            ]

            args = [
                ("1981-01-01", "<gs://my/zarr/root>", fname, slice_chunks[ii])
                for ii in range(4)
            ]

            pool.starmap(populate_historic_single, args)

        else:
            populate_historic_single(
                "1981-01-01",
                "gs://my/zarr/root",
                fname,
                slices,
            )

        os.remove(fname)

    return 1


if __name__ == "__main__":

    populate_historic_loop(
        multi=True,
        path_template="my-bucket/path/file.nc",
        year_range=list(range(2002, 2022)),
        path_root="/my/local/tmp/path",
        slices_path="/my/nonzero/slices.pkl",
    )

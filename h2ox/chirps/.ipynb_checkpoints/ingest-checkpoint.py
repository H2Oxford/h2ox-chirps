import multiprocessing as mp
import os
import pickle
from datetime import datetime
from typing import List, Union

import numpy as np
import zarr
from gcsfs import GCSFileSystem
from skimage import io
from tqdm import tqdm


def pipeline_daily_tif(
    tif_dt_str: str,
    zero_dt_str: str,
    tif_name: str,
    multi: bool,
    archive_path: str,
    slices_path: str,
):

    # load_slices
    slices = pickle.load(open(slices_path, "rb"))

    # ingest tif
    if multi:

        CPUS = os.cpu_count()
        pool = mp.Pool(CPUS)

        chunk_size = len(slices) // CPUS + 1
        slice_chunks = [
            slices[ii * chunk_size : (ii + 1) * chunk_size] for ii in range(CPUS)
        ]

        args = [
            (
                tif_name,
                archive_path,
                slice_chunks[ii],
                zero_dt_str,
                tif_dt_str,
                False,
            )
            for ii in range(CPUS)
        ]

        pool.starmap(ingest_tif, args)

    else:

        ingest_tif(
            tif_path=tif_name,
            archive_path=archive_path,
            slices=slices,
            zero_dt_str=zero_dt_str,
            tif_dt_str=tif_dt_str,
            verbose=False,
        )

    return 1


def ingest_tif(
    tif_path: str,
    archive_path: str,
    slices: Union[List, str],
    zero_dt_str: str,
    tif_dt_str: str,
    verbose: bool,
):

    zero_dt = datetime.strptime(zero_dt_str, "%Y-%m-%d")
    tif_dt = datetime.strptime(tif_dt_str, "%Y-%m-%d")

    time_idx = (tif_dt - zero_dt).days

    mapper = GCSFileSystem().get_mapper
    z = zarr.open(mapper(archive_path), "r+")["precip"]

    if isinstance(slices, str):
        slices = pickle.load(open(slices, "rb"))

    im = np.flip(io.imread(tif_path), axis=0)
    im[im < 0] = np.nan

    if verbose:
        pbar = tqdm(slices, total=len(slices), desc=os.path.split(tif_path)[-1])
    else:
        pbar = slices

    for s in pbar:

        z[s[0], s[1], time_idx] = im[s[0], s[1]]

    return 1

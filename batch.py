import os
from main import main_loop

from datetime import datetime
from h2ox.chirps.slackbot import SlackMessenger

import zarr
import numpy as np
    
if __name__=="__main__":
    
    ### test zarr stuff
    z_url = "oxeo-chirps/test"
    mapper = GCSFileSystem().get_mapper
    
    z = zarr.open(mapper(z_url), mode='w', shape=(10000, 10000), chunks=(1000, 1000), dtype='i4')
    z[:] = 42
    z[0, :] = np.arange(10000)
    z[:, 0] = np.arange(10000)
    
    token=os.environ.get("SLACKBOT_TOKEN")
    target=os.environ.get("SLACKBOT_TARGET")
    
    if token is not None and target is not None:

        slackmessenger = SlackMessenger(
            token=token,
            target=target,
            name="h2ox-chirps",
        )
    else:
        slackmessenger=None
        
    main_loop(today=datetime.now(), slackmessenger=slackmessenger)
    
    
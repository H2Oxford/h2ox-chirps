import os
from main import main_loop

from datetime import datetime
from h2ox.chirps.slackbot import SlackMessenger
    
if __name__=="__main__":
    
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
    
    
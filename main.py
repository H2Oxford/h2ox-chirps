import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional

from flask import Flask, request
from loguru import logger

from h2ox.chirps import pipeline_daily_tif
from h2ox.chirps.slackbot import SlackMessenger
from h2ox.chirps.utils import (
    create_task,
    deploy_task,
    download_cloud_json,
    download_or_code,
    upload_blob,
)

app = Flask(__name__)


if __name__ != "__main__":
    # Redirect Flask logs to Gunicorn logs
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info("Service started...")
else:
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


def format_stacktrace():
    parts = ["Traceback (most recent call last):\n"]
    parts.extend(traceback.format_stack(limit=25)[:-2])
    parts.extend(traceback.format_exception(*sys.exc_info())[1:])
    return "".join(parts)


@app.route("/", methods=["POST"])
def main():
    """Receive a request and queue downloading CHIRPS data

    Request params:
    ---------------

        today: str


    # download forecast (tigge or HRES)
    # ingest to zarr

    #if pubsub:
    envelope = request.get_json()
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    request_json = envelope["message"]["data"]

    if not isinstance(request_json, dict):
        json_data = base64.b64decode(request_json).decode("utf-8")
        request_json = json.loads(json_data)

    logger.info('request_json: '+json.dumps(request_json))

    # parse request
    today_str = request_json['today']

    """

    time.time()

    payload = request.get_json()

    if not payload:
        msg = "no message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    logger.info("payload: " + json.dumps(payload))
    logger.info("environ")
    logger.info(f"{os.environ.keys()}")

    if not isinstance(payload, dict):
        msg = "invalid task format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400
    
    token=os.environ.get("SLACKBOT_TOKEN")
    target=os.environ.get("SLACKBOT_TARGET")
    
    if token is not None and target is not None:

        slackmessenger = SlackMessenger(
            token=token,
            target=target,
            name="h2ox-chirps",
        )
    else:
        slackmessenger = None

    today_str = payload["today"]

    today = datetime.strptime(today_str, "%Y-%m-%d").replace(tzinfo=None)

    return main_loop(today, slackmessenger)


def main_loop(
    today: datetime,
    slackmessenger: Optional[SlackMessenger] = None,
    archive_path: Optional[str] = None,
    token_path: Optional[str] = None,
    prelim_url_template: Optional[str] = None,
    post_url_template: Optional[str] = None,
    zero_dt_str: Optional[str] = None,
    multi: Optional[bool] = None,
    requeue: Optional[bool] = None,
):

    if archive_path is None:
        archive_path = os.environ.get("ARCHIVE_PATH")
    if token_path is None:
        token_path = os.environ.get("TOKEN_PATH")
    if prelim_url_template is None:
        prelim_url_template = os.environ.get(
            "PRELIM_URL"
        )  # https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_daily/fixed/tifs/2022/chirps-v2.0.2022.01.02.tif
    if post_url_template is None:
        post_url_template = os.environ.get(
            "POST_URL"
        )  # https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/2022/chirps-v2.0.2022.02.28.tif
    if zero_dt_str is None:
        zero_dt_str = os.environ.get("ZERO_DT")
    if multi is None:
        multi = str(os.environ.get("MULTI")).lower() == "true"
    if requeue is None:
        requeue = str(os.environ.get("REQUEUE")).lower() == "true"

    storage_root = os.path.join(os.getcwd(), "data")
    slices_path = os.path.join(os.getcwd(), "data", "nonzero_slices.pkl")

    # read the token on the bucket to get archive most recent prelim
    token = download_cloud_json(token_path)

    last_prelim = datetime.strptime(token["last_prelim"], "%Y-%m-%d")
    last_post = datetime.strptime(token["last_post"], "%Y-%m-%d")

    # do prelims first
    done_prelim = []
    for add_day_prelim in range(
        1, (today - last_prelim).days + 1
    ):  # plus 1 so it does today
        do_dt = last_prelim + timedelta(days=add_day_prelim)

        url = prelim_url_template.replace("YEAR", str(do_dt.year)).replace(
            "DATE", do_dt.isoformat()[0:10].replace("-", ".")
        )

        tif_name = os.path.join(storage_root, do_dt.isoformat()[0:10] + ".tif")

        code = download_or_code(url, tif_name)

        time.sleep(5)
        
        if code == 200:

            logger.info(f"ingesting prelim {tif_name}")

            pipeline_daily_tif(
                tif_dt_str=do_dt.isoformat()[0:10],
                zero_dt_str=zero_dt_str,
                tif_name=tif_name,
                archive_path=archive_path,
                multi=multi,
                slices_path=slices_path,
            )

            token["last_prelim"] = do_dt.isoformat()[0:10]
            done_prelim.append(do_dt.isoformat()[0:10])

            # write after each finished - so can restart from failed tasks
            local_token_path = os.path.join(os.getcwd(), "token.json")
            json.dump(token, open(local_token_path, "w"))
            upload_blob(local_token_path, token_path)

            os.remove(tif_name)

        else:
            # reached most recent, break loop
            logger.info(f"not found: {do_dt.isoformat()[0:10]}, breaking")
            break

    # do post
    done_post = []
    for add_day_post in range(1, (today - last_post).days + 1):
        do_dt = last_post + timedelta(days=add_day_post)

        url = post_url_template.replace("YEAR", str(do_dt.year)).replace(
            "DATE", do_dt.isoformat()[0:10].replace("-", ".")
        )

        tif_name = os.path.join(storage_root, do_dt.isoformat()[0:10] + ".tif")

        code = download_or_code(url, tif_name)

        if code == 200:

            logger.info(f"ingesting post {tif_name}")

            pipeline_daily_tif(
                tif_dt_str=do_dt.isoformat()[0:10],
                zero_dt_str=zero_dt_str,
                tif_name=tif_name,
                archive_path=archive_path,
                multi=multi,
                slices_path=slices_path,
            )

            token["last_post"] = do_dt.isoformat()[0:10]

            # write after each finished - so can restart from failed tasks
            local_token_path = os.path.join(os.getcwd(), "token.json")
            json.dump(token, open(local_token_path, "w"))
            upload_blob(local_token_path, token_path)

            done_post.append(do_dt.isoformat()[0:10])

            os.remove(tif_name)

        else:
            # reached most recent, break loop
            logger.info(f"not found: {do_dt.isoformat()[0:10]}, breaking")
            break

    logger.info(
        f'Pushing token: last_prelim={token["last_prelim"]}, last_post={token["last_post"]}'
    )

    if slackmessenger is not None:
        slackmessenger.message(
            f"CHIRPS ::: done prelim: {','.join(done_prelim)}; done post: {','.join(done_post)}"
        )

    if requeue:
        enqueue_tomorrow(today)

    return "Ingesting CHIRPS complete", 200


def enqueue_tomorrow(today):

    tomorrow = today + timedelta(hours=24)

    cfg = dict(
        project=os.environ["project"],
        queue=os.environ["queue"],  # queue name
        location=os.environ["location"],  # queue
        url=os.environ["url"],  # service url
        service_account=os.environ["service_account"],  # service acct
    )

    task = create_task(
        cfg=cfg,
        payload=dict(today=tomorrow.isoformat()[0:10]),
        task_name=tomorrow.isoformat()[0:10],
        delay=24 * 3600,
    )

    deploy_task(cfg, task)

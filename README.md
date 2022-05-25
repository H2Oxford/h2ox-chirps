[<img alt="Wave2Web Hack" width="1000px" src="https://github.com/H2Oxford/.github/raw/main/profile/img/wave2web-banner.png" />](https://www.wricitiesindia.org/content/wave2web-hack)

H2Ox is a team of Oxford University PhD students and researchers who won first prize in the[Wave2Web Hackathon](https://www.wricitiesindia.org/content/wave2web-hack), September 2021, organised by the World Resources Institute and sponsored by Microsoft and Blackrock. In the Wave2Web hackathon, teams competed to predict reservoir levels in four reservoirs in the Kaveri basin West of Bangaluru: Kabini, Krishnaraja Sagar, Harangi, and Hemavathy. H2Ox used sequence-to-sequence models with meterological and forecast forcing data to predict reservoir levels up to 90 days in the future.

The H2Ox dashboard can be found at [https://h2ox.org](https://h2ox.org). The data API can be found at [https://github.com/Lkruitwagen/wave2web-api](https://github.com/Lkruitwagen/wave2web-api). Our Prototype Submission Slides are [here](https://docs.google.com/presentation/d/1J_lmFu8TTejnipl-l8bXUZdKioVseRB4tTzqK6sEokI/edit?usp=sharing). The H2Ox team is [Lucas Kruitwagen](https://github.com/Lkruitwagen), [Chris Arderne](https://github.com/carderne), [Tommy Lees](https://github.com/tommylees112), and [Lisa Thalheimer](https://github.com/geoliz).

# H2Ox CHIRPS
This repo is for a dockerised service to import UCSB Climate Hazard Center's [CHIRPS](https://www.chc.ucsb.edu/data/chirps) (Climate Hazards Group InfraRed Precipitation with Station) data into a [Zarr archive](https://zarr.readthedocs.io/en/stable/). The Zarr data is rechunked in the time domain in blocks of four years. This ensures efficient access to moderately-sized chunks of data, facilitating timeseries research. Data is ingested twice: once when it is issued as 'preliminary' (which is issued in pentads with at most a 5-day lag) and again when it is issued as 'post' (which is issued about once a month).

## Installation

This repo can be `pip` installed:

    pip install https://github.com/H2Oxford/h2ox-chirps.git
    
For development, the repo can be pip installed with the `-e` flag and `[dev]` options:

    git clone https://github.com/H2Oxford/h2ox-chirps.git
    cd h2ox-chirps
    pip install -e .[dev]
    
For containerised deployment, a docker container can be built from this repo:

    docker build -t <my-tag> .
    
Cloudbuild container registery services can also be targeted at forks of this repository.

## Useage

### Ingestion

The Flask app in `main.py` listens for a POST http request and then triggers the ingestion workflow.
The http request must have a json payload with a YYYY-mm-dd datetime string keyed to "today": `{"today":"<YYYY-mm-dd>"}`.
The ingestion script finds tokens on cloud storage which indicate the most recent data to be ingested, ingests new data from the CHIRPS servers, and then updates the ingestion token.
A simple [slackbot](https://slack.com/intl/en-gb/help/articles/115005265703-Create-a-bot-for-your-workspace#:~:text=A%20bot%20is%20a%20nifty,a%20bot%20for%20your%20workspace.) messenger is included to send ingestion updates to a slack channel.

The following environment variables are required:

    SLACKBOT_TOKEN=<my-slackbot-token>      # a token for a slack-bot messenger
    SLACKBOT_TARGET=<my-slackbot-target>    # target channel to issue ingestion updates
    ARCHIVE_PATH=<gs://my/archive/path>     # the path to the target Zarr archive
    TOKEN_PATH=<gs://my/path/to/token.json> # the path to a .json token which captures the most recent ingested data.
    PRELIM_URL_TEMPLATE=<http://https://data.chc.ucsb.edu/path/to/preliminary/chirps/yyyy-mm-dd.tif> # a sample url to prelim CHIRPS data
    POST_URL_TEMPLATE=<http://https://data.chc.ucsb.edu/path/to/chirps/yyyy-mm-dd.tif> # a sample url to post CHIRPS data
    ZERO_DT=<YYYY-mm-dd>                    # the initial date-time of the zarr archive
    
The following environment variables are optional:

    MULTI=<true|false>       # ingest with multiprocessing
    REQUEUE=<true|false>     # requeue a task for tomorrow's ingestion
    
If using `REQUEUE`, the ingestion script will push a task to a [cloud task queue](https://cloud.google.com/tasks/docs/creating-queues) to enqueue ingestion for tomorrow. This way a continuous service is created that runs daily. The additional environment variables will be required:

    project=<my-gcp-project>            # gcp project associated with queue and cloud storage
    queue=<my-queue-name>               # queue name where pending tasks can be places
    location=<my-queue-region>          # location name for task queue
    url=<http://my/dockerised/service>  # url of the entrypoint for the docker container to be run
    service_account=<myacct@email.com>  # service account for submitting tasks and http request


Environment variables can be put in a `.env` file and passed to the docker container at runtime:

    docker run --env-file=.env -t <my-tag>
    
### Accessing ingested data

[xarray](https://docs.xarray.dev/en/stable/) can be used with a zarr backend to lazily access very large zarr archives.

<img alt="Zarr Xarray" width="1000px" src="https://github.com/H2Oxford/.github/raw/main/profile/img/zarr_chirps.png"/>


## Citation

CHIRPS can be cited as:

    Funk, C.C., Peterson, P.J., Landsfeld, M.F., Pedreros, D.H., Verdin, J.P., Rowland, J.D., Romero, B.E., Husak, G.J., Michaelsen, J.C., and Verdin, A.P., 2014, A quasi-global precipitation time series for drought monitoring: U.S. Geological Survey Data Series 832, 4 p. http://pubs.usgs.gov/ds/832/
    
Our Wave2Web submission can be cited as: 
 
    <citation here>
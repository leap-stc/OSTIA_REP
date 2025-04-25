"""Recipe for generating a Zarr store from the OSTIA rep dataset hosted at NASA PODAAC
Note: There were a few caveats in processing this dataset
1. PODAAC data need credentials to access. We used the library `earthaccess` to get auth
2. The AWS version of this data is region restricted to us-west-2, so you compute needs to be in that region
or.. you can configure earthaccess with `indirect` to use https links
3. This was run on a large machine! r8g.24xlarge in us-west-2
4. The python library + Zarr python >= 3.0.7 was used for writing to LEAP's OSN pod"""

import earthaccess
import xarray as xr
import zarr
from distributed import Client
from obstore.store import S3Store
from zarr.storage import ObjectStore

zarr.config.set({'async.concurrency': 100})


# see note #3
client = Client(n_workers=96)
client

# you need to pass in valid earthdata creds or save them in a config file
auth = earthaccess.login(persist=True)

# grab all of OSTIA-UKMO-L4-GLOB-REP-v2.0
results = earthaccess.search_data(
    short_name='OSTIA-UKMO-L4-GLOB-REP-v2.0', temporal=('1982-01-01', '2023-12-31')
)
file_handles = earthaccess.open(results)


# big open_mfdataset! Needs a large machine for this approach.
ds = xr.open_mfdataset(
    file_handles, chunks={}, parallel=True, coords='minimal', data_vars='minimal', compat='override'
)


# configure the obstore backed Zarr store for LEAP OSN
osnstore = S3Store(
    'leap-pangeo-pipeline',
    prefix='OSTIA/OSTIA.zarr',
    aws_endpoint='https://nyu1.osn.mghpcc.org',
    access_key_id='<INSERT>',
    secret_access_key='<INSERT>',
    client_options={'allow_http': True},
)
zstore = ObjectStore(osnstore)


# Chunk from 1 to 5 to reach ~100MB chunks
ds.chunk({'time': 5}).to_zarr(
    zstore,
    zarr_format=3,
    consolidated=False,
    mode='w',
)

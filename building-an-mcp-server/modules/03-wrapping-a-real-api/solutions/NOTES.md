# Notes: Module 03 (reference answers)

Code is in [`files/`](files/): `depintel_server.py` (all five exercises) and `test_depintel.py` (tests for 2 and 4).

## Exercise 1: `latest_safe_version(name, current)`

Fetch the release list from PyPI, keep releases >= `current` in PEP 440 order (`packaging.version`, not string
order: `2.10` > `2.9`), and return the first one OSV reports clean. If `current` itself is clean, return it.
The loop is bounded (25 candidates) so one call cannot fan out into hundreds of upstream requests. Choosing the
*lowest* safe version keeps the suggested upgrade small. A smarter version would prefer the same major version
and show the `fixed_in` data alongside.

## Exercise 2: TTL cache for PyPI lookups

The cache lives in `AppState` (created in the lifespan), so it is per server instance and tests stay isolated.
Only successful PyPI `GET`s are cached, never errors (or a transient 503 gets stuck for 60 s). OSV `POST`s are not
cached because vulnerability data changes. `test_pypi_cache_avoids_second_request` counts transport calls:
two identical `package_info` calls give one HTTP request.

## Exercise 3: `pypi://{name}/{version}/metadata`

A resource is better when the **host or user** decides what context to attach rather than the model deciding to
act: for example, a host that shows a dependency diff can attach the metadata of each changed pin. It is also
better when the content is addressable and cacheable. An exact release never changes, so the host can cache it
indefinitely and deduplicate by URI. `package_info` stays a tool because the model calls it mid-task, and "latest"
is a moving target.

## Exercise 4: OSV `/v1/querybatch`

One `POST /v1/querybatch` with all pinned lines replaces N `POST /v1/query` calls, which also makes the
`CapacityLimiter` unnecessary. The batch response only has `id` and `modified` per vulnerability, which is all
`audit_requirements` reports. Latency, measured against the live API on 2026-10-19 with a 20-line file (17
vulnerable pins): per-line queries took 1.1-1.3 s and the batch took 0.85-1.05 s, so about 20-25% faster. The
win is smaller than the request count suggests because the limiter already ran 8 queries in parallel. The bigger
gain is politeness (1 request instead of 20). The trade-off: one failed batch now fails every line. Measure your own
with `time`.

## Exercise 5: Retry hints

429/502/503/504 now produce `isError: true` with "This is temporary: retry this call after N seconds" (using
`Retry-After` when present), while 404 and 4xx still read as permanent. What to look for in a real host: whether
the model retries automatically, waits, or asks the user. The course author did not observe a real host for this
edition (no host on the build machine), so record your own result. Hosts differ, and a clear "temporary, retry
after N s" message is the only lever the server has.

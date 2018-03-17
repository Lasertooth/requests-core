Requests-Core
=============

**Experimental lower-level async HTTP client for Requests 3.0**

--------------

**Goals**:

- take urllib3 codebase
- add async support (with multiple backends)
- default to trio execution of async functions for blocking calls.
- potentially, add h2 support (would be amazing, if feasable)

Usage
-----

Async usage::

    import requests_core

    url = "http://httpbin.org/uuid"

    async def main():
        r = await requests_core.request(method='GET', url=url, timeout=2)
        print(r.headers)
        print(await r.read())


::

    >>> import trio
    >>> trio.run(main)
        HTTPHeaderDict({'connection': 'keep-alive', 'server': 'meinheld/0.6.1', 'date': 'Fri, 16 Mar 2018 11:59:57 GMT', 'content-type': 'application/json', 'access-control-allow-origin': '*', 'access-control-allow-credentials': 'true', 'x-powered-by': 'Flask', 'x-processed-time': '0', 'content-length': '53', 'via': '1.1 vegur'})
        b'{\n  "uuid": "693947c9-9f49-4b4a-be94-73a152ce1acb"\n}\n'

Sync usage::

    >>> r = requests_core.blocking_request(method='GET', url=url, timeout=2)
    >>> print(r)
    <requests_core._http._async.response.HTTPResponse object at 0x103f63c88>


Installation
------------

This is a work in progress. Don't install it.

# scrubdash
Dashboard for organizing, visualizing, and analyzing images coming in from a ScrubCam(s)

## Installation
```python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps scrubdash```

## Usage
```
Useage:
    scrubdash [options] <config_file>
    
Options:
    --cont  Continue the most recent session
```

## Example
```
$ scrubdash -c cfgs/config.yaml
[INFO] Server Started (scrubdash.asyncio_server.asyncio_server)
[INFO] Configuration finished (scrubdash.asyncio_server.asyncio_server)
Dash is running on http://0.0.0.0:8050/

[INFO] Dash is running on http://0.0.0.0:8050/
 (scrubdash.dash_server.app)
 * Serving Flask app 'scrubdash.dash_server.app' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
[WARNING]  * Running on all addresses.
   WARNING: This is a development server. Do not use it in a production deployment. (werkzeug)
[INFO]  * Running on http://172.22.126.191:8050/ (Press CTRL+C to quit) (werkzeug)
```

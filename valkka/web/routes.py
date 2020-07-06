import pathlib

def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('clips', 'clips', cache_max_age=3600)

    config.add_route('home', '/')

    config.add_route('async_get', '/async_get')     # async get demo page
    config.add_route('async_get2', '/async_get2')   # async get is performed to this address

    config.add_route('download', '/download')       # download demo page
    config.add_route('download2', '/download2')     # downloadable file is found here

    config.add_route('session', '/session')
    config.add_route('session_push', '/session_push')
    config.add_route('session_clear', '/session_clear')

    config.add_route('shaka','/shaka')

    config.add_route('myauth','/myauth')
    config.add_route('login','/login')
    config.add_route('logout','/logout')
    config.add_route('websocket','/websocket')
    

    """
    # # handling of static asssets that are compiled (webpack, etc.)    
    # # see also: https://docs.pylonsproject.org/projects/pyramid-cookbook/en/latest/static_assets/bundling-static-assets.html
    # after default static view add bundled static support
    config.add_static_view(
        "static_bundled", "static_bundled", cache_max_age=1
    )
    path = pathlib.Path(config.registry.settings["statics.dir"])
    # create the directory if missing otherwise pyramid will not start
    path.mkdir(exist_ok=True)
    config.override_asset(
        to_override="yourapp:static_bundled/",
        override_with=config.registry.settings["statics.dir"],
    )
    """
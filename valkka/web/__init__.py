from pyramid.config import Configurator

# auth stuff
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

def main(global_config, **settings):
    """This function returns a Pyramid WSGI application.
    """
    # Security policies
    authn_policy = AuthTktAuthenticationPolicy(
        settings['authtest.secret'], # callback=groupfinder,
        hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()

    with Configurator(settings=settings) as config:
        config.include('pyramid_redis_sessions')
        config.include('pyramid_jinja2')
        config.include('.routes')
        config.include('.security')
        config.set_authentication_policy(authn_policy)
        config.set_authorization_policy(authz_policy)
        config.scan()

    return config.make_wsgi_app()


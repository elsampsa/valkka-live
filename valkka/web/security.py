from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

# from .models import User


class MyAuthenticationPolicy(AuthTktAuthenticationPolicy):
    def authenticated_userid(self, request):
        user = request.user # this maps to get_user => signed cookie
        if user is not None:
            return user.id

def get_user(request):
    # unauthenticated_userid comes from the cookie
    user_id = request.unauthenticated_userid
    print("get_user: user_id=", user_id)
    """
    if user_id is not None:
        user = request.dbsession.query(User).get(user_id)
        return user
    """
    if user_id is not None: # let's return a dummy user
        user = {"name":"kikkelis", "surname":"kokkelis"}
        print("get_user:", user)
        return user


def includeme(config):
    settings = config.get_settings()
    authn_policy = MyAuthenticationPolicy(
        settings['authtest.secret'],
        hashalg='sha512',
    )
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.add_request_method(get_user, 'user', reify=True)
    # from now, on, request will have the member "user"
    # https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hooks.html#adding-methods-or-properties-to-a-request-object

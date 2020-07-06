import time
from pyramid.httpexceptions import HTTPFound
from pyramid.security import (
    remember,
    forget,
    )
from pyramid.view import (
    forbidden_view_config,
    view_config,
)
from pyramid.response import Response, FileResponse

class AuthView:

    def __init__(self, request):
        self.request = request
    
    @view_config(route_name="myauth", renderer="../templates/auth.jinja2")
    def myauth(self):
        user = self.request.user
        if user is None:
            print("not logged in")
            is_auth = False
        else:
            print("logged in allright")
            is_auth = True
        return {"is_auth" : is_auth}


    @view_config(route_name='login') # , renderer="../templates/auth.jinja2")
    def login(self):
        print("login")
        """# if request has been attached an attribute "next"
        next_url = request.params.get('next', request.referrer)
        if not next_url:
            next_url = request.route_url('view_wiki')
        message = ''
        login = ''
        """
        user = self.request.params.get("user", None)
        passwd = self.request.params.get("passwd", None)

        print(user, passwd)

        if user is None or passwd is None:
            return HTTPFound()

        # check for user & passwd from the db
        _id = str(time.time()) # suppose this is user's unique id
        headers = remember(self.request, _id)
        # return Response(headers=headers) 
        # that one sets auth info into the cookies in the header
        # .. and so that information becomes persistent
        
        # can also send a json object ..
        # .. with the headers
        # return HTTPFound(headers=headers) # uh.. this loops N times

        print("login: returning with headers", headers)
        # # we didn't come here through href, i.e. through a link, so 
        # # the page won't get re-directed!
        # return HTTPFound(location=self.request.route_url('home'), headers=headers)  
        # doesn't reload the page, of course

        return Response(json = {"auth": True}, headers = headers) # works allright
        # # so, the only thing the response does here, is to set
        # # the headers => cookies in the browser that receives the response
        # # nothing is rendered, since we didn't come here through href

        # return Response(json = {"auth": True}) # nopes

        """# URL forward
        if 'form.submitted' in request.params:
            login = request.params['login']
            password = request.params['password']
            user = request.dbsession.query(User).filter_by(name=login).first()
            if user is not None and user.check_password(password):
                headers = remember(request, user.id)
                return HTTPFound(location=next_url, headers=headers)
            message = 'Failed login'
        
        return dict(
            message=message,
            url=request.route_url('login'),
            next_url=next_url,
            login=login,
            )
        """

    @view_config(route_name='logout')
    def logout(self):
        print("logout")
        headers = forget(self.request)
        # next_url = request.route_url('view_wiki')
        # return HTTPFound(location=next_url, headers=headers)
        # return Response(json = {"auth": False}, headers = headers)
        return HTTPFound(location=self.request.route_url('myauth'), headers=headers)


    """
    @forbidden_view_config()
    def forbidden_view(request):
        next_url = request.route_url('login', _query={'next': request.url})
        return HTTPFound(location=next_url)
    """

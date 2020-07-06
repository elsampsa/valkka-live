 
from pyramid.view import view_config
from pyramid.response import Response, FileResponse
from pyramid.httpexceptions import HTTPUnauthorized, HTTPNotFound, HTTPFound

import time

class SessionView:

    def __init__(self, request):
        """This is called always when you access the session demo page
        """
        self.request = request
        self.session = self.request.session
        self.initSession("data_list", default = [])
        # now we have self.data_list that refers to self.request.session.data_list
        # if it wasn't in the cache, it is set to [] (i.e. empty list)


    def initSession(self, key, default = None):
        """Init something to self.request.session where redis cached data lives
        """
        if key not in self.session:
            self.session[key] = default
            self.session.changed() # re-serialize


    @view_config(route_name = "session", renderer = "../templates/session.jinja2")
    def session_view(self):
        """Return cached data to the template renderer
        """
        res = {
            "data_list" : self.session["data_list"] # self.data_list lives in the cache (refers to self.request.session)
        }
        return res


    @view_config(route_name = "session_push")
    def session_push(self):
        """Push more data to cache
        """
        # new_data = self.request.params.get("data", None) # if the key "data" had been passed with GET
        new_data = "timestamp: %i" % int(time.time()*1000)
        # self.request.session["data_list"].append(new_data)
        self.session["data_list"].append(new_data) # self.data_list lives in the cache (refers to self.request.session)
        self.session.changed()
        print("session_push: data_list: ", self.session["data_list"])
        return HTTPFound(location='/session') # redirect


    @view_config(route_name = "session_clear")
    def session_clear(self):
        """Clear cached data
        """
        self.session["data_list"] = [] # self.data_list lives in the cache (refers to self.request.session)
        self.session.changed()
        return HTTPFound(location='/session') # redirect



    
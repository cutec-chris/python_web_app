import bottle,sys,threading,uuid,logging
Sessions = []
_app = None
_srv = None
_server_thread = None
class BaseSessionElement(object): pass
SessionElement = BaseSessionElement
def Session(sid=None):
    try:
        if sid is None:
            sid = bottle.request.params['sid']
    except: pass
    #if sid is None:
    #    sid = bottle.request.get_cookie("sid")
    res = None
    for session in Sessions:
        if session.sid == sid:
            res = session
            break
    if res == None:
        global SessionElement
        res = SessionElement()
        Sessions.append(res)
        res.sid = str(uuid.uuid1())
    #bottle.response.set_cookie('sid',res.sid)
    try:
        res.Enter()
    except BaseException as e:
        pass
    return res
def Server():
    return _srv
def CustomSessionElement(se):
    global SessionElement
    SessionElement = se
def run(app=None,**kwargs):
    if app == None:
        app = bottle.default_app()
    import wsgiref.simple_server,socketserver
    class ThreadingWSGIServer(socketserver.ThreadingMixIn, wsgiref.simple_server.WSGIServer):
        daemon_threads = True
    class WSGIRefServer(bottle.ServerAdapter):
        def run(self, app): # pragma: no cover
            from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
            from wsgiref.simple_server import make_server
            import socket
            class FixedHandler(WSGIRequestHandler):
                server_version = 'Webapp/0.0.2'
                def address_string(self): # Prevent reverse DNS lookups please.
                    return self.client_address[0]
                def log_request(*args, **kw):
                    if not self.quiet:
                        return WSGIRequestHandler.log_request(*args, **kw)
                def get_environ(self):
                    env = super().get_environ()
                    if self.client_address[1]:
                        env['REMOTE_PORT'] = self.client_address[1]
                    return env
            handler_cls = self.options.get('handler_class', FixedHandler)
            server_cls  = self.options.get('server_class', ThreadingWSGIServer)
            if ':' in self.host: # Fix wsgiref for IPv6 addresses.
                if getattr(server_cls, 'address_family') == socket.AF_INET:
                    class server_cls(server_cls):
                        address_family = socket.AF_INET6
            self.srv = make_server(self.host, self.port, app, server_cls, handler_cls)
            self.srv.serve_forever()
    global _srv
    _srv = WSGIRefServer(host='0.0.0.0',port='8123')
    opt = dict(server=_srv)
    if '--debug' in sys.argv[1:]:
        logging.warning("entering debug mode")
        opt['debug']=True
        opt['reloader']=True
    if 'reloader' in kwargs:
        opt['reloader'] = kwargs.get('reloader',)
    if 'debug' in kwargs:
        opt['debug'] = kwargs.get('debug',opt['debug'])
    global _server_thread
    _server_thread = threading.Thread(target=app.run, kwargs=opt, daemon=True)
    _server_thread.start()
    global _app
    _app = app
def DoTick():
    global _server_thread
    if _server_thread is not None and _server_thread.is_alive():
        _server_thread.join(.5)
    return _server_thread == None or _server_thread.is_alive()
def DoStop():
    global _app,_srv,_server_thread
    logging.warning('stopping server ...')
    _app.close()
    try:
        _srv.srv.shutdown()
    except:
        pass
    _server_thread.join(.5)
def redirect(location, code=303):
    try:
        bottle.redirect(location, code)
    except bottle.HTTPResponse as res:
        return res
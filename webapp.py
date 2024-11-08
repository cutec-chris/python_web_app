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
    for session in reversed(Sessions):
        if session.sid == sid or ((sid == 'first') and (hasattr(session,'rtest'))):
            res = session
            break
    #trial to fingerprint browser
    remote_addr = bottle.request.environ.get('HTTP_X_FORWARDED_FOR') or bottle.request.environ.get('REMOTE_ADDR')
    if bottle.request.environ.get('REMOTE_PORT'):
        remote_addr += ':'+str(bottle.request.environ.get('REMOTE_PORT'))
    remote_addr += '///'+bottle.request.headers['User-Agent']
    if res == None: 
        for session in Sessions:
            if session.remote_addr == remote_addr:
                res = session
                break
    if res == None:
        global SessionElement
        res = SessionElement()
        Sessions.append(res)
        res.sid = str(uuid.uuid4())
        res.remote_addr = remote_addr
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
                        try:
                            return WSGIRequestHandler.log_request(*args, **kw)
                        except: pass
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
        bottle.response.status = code
        bottle.response.set_header('Location', location)
        return bottle.response
def ColoredOutput(level):
    def set_color(alevel, code):
        level_fmt = "\033[1;" + str(code) + "m%s\033[1;0m" 
        logging.addLevelName( alevel, level_fmt % logging.getLevelName(alevel) )
    std_stream = sys.stdout
    isatty = getattr(std_stream, 'isatty', None)
    if isatty and isatty():
        levels = [logging.DEBUG, logging.CRITICAL, logging.WARNING, logging.ERROR]
        set_color(logging.WARNING, 34)
        set_color(logging.ERROR, 31)
        set_color(logging.CRITICAL, 45)
        for idx, blevel in enumerate(levels):
            set_color(blevel, 30 + idx )
    logging.basicConfig(stream=std_stream, level=level)
    logging.root.setLevel(level)    
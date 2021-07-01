import bottle,sys,threading,uuid
Sessions = []
class SessionElement(object): pass
def Session():
    sid = bottle.request.get_cookie("sid")
    res = None
    for session in Sessions:
        if session.sid == sid:
            res = session
    if res == None:
        res = SessionElement()
        Sessions.append(res)
        res.sid = str(uuid.uuid1())
    bottle.response.set_cookie('sid',res.sid)
    return res
server_thread = None
def run(app):
    class WSGIRefServer(bottle.ServerAdapter):
        def run(self, app): # pragma: no cover
            from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
            from wsgiref.simple_server import make_server
            import socket
            class FixedHandler(WSGIRequestHandler):
                server_version = 'test/0.0.1'
                def address_string(self): # Prevent reverse DNS lookups please.
                    return self.client_address[0]
                def log_request(*args, **kw):
                    if not self.quiet:
                        return WSGIRequestHandler.log_request(*args, **kw)
            handler_cls = self.options.get('handler_class', FixedHandler)
            server_cls  = self.options.get('server_class', WSGIServer)
            if ':' in self.host: # Fix wsgiref for IPv6 addresses.
                if getattr(server_cls, 'address_family') == socket.AF_INET:
                    class server_cls(server_cls):
                        address_family = socket.AF_INET6
            self.srv = make_server(self.host, self.port, app, server_cls, handler_cls)
            self.srv.serve_forever()
    import wsgiref.simple_server,socketserver
    class ThreadingWSGIServer(socketserver.ThreadingMixIn, wsgiref.simple_server.WSGIServer):
        daemon_threads = True
    srv = WSGIRefServer(server_cls=ThreadingWSGIServer,port='8123')
    opt = dict(server=srv)
    if '--debug' in sys.argv[1:]:
        logging.warning("entering debug mode")
        opt['debug']=True
        opt['reloader']=True
    server_thread = threading.Thread(target=app.run, kwargs=opt)
    server_thread.start()
def DoTick():
    if server_thread is not None and server_thread.is_alive():
        server_thread.join(.5)
    return server_thread == None or server_thread.is_alive()
def DoStop():
    logging.warning('stopping server ...')
    app.close()
    srv.srv.shutdown()
    server_thread.join(.5)

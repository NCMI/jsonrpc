from twisted.internet import reactor, ssl
from twisted.web import server

from .server import ServerEvents, JSON_RPC

class JSONRPCTest(ServerEvents):
	def callmethod(self, request, method, kwargs, args, **kw):
		if method in set(['add', 'subtract']):
			return getattr(self, method)(*args, **kwargs)

	def subtract(self, a, b):
		return a-b

	def add(self, a, b):
		return a+b

root = JSON_RPC().customize(JSONRPCTest)
site = server.Site(root)


# 8007 is the port you want to run under. Choose something >1024
reactor.listenTCP(8007, site)
reactor.run()


__version__ = "$Revision: 1.8 $".split(":")[1][:-1].strip()

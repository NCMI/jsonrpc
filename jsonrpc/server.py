# $Id: server.py,v 1.8 2011/05/26 19:34:19 edwlan Exp $

#
#  Copyright (c) 2011 Edward Langley
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#  Redistributions of source code must retain the above copyright notice,
#  this list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  Neither the name of the project's author nor the names of its
#  contributors may be used to endorse or promote products derived from
#  this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#  TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
import jsonrpc.jsonutil
from jsonrpc.utilities import public

# Twisted imports
from twisted.web import server
from twisted.internet import threads
from twisted.web.resource import Resource


import UserDict, collections
collections.Mapping.register(UserDict.DictMixin)

@public
class ServerEvents(object):
	'''Subclass this and pass to :py:meth:`jsonrpc.customize` to customize the jsonrpc server'''

	def __init__(self, server):
		#: A link to the JSON-RPC server instance
		self.server = server

	def callmethod(self, txrequest, rpcrequest):
		'''Finds the method and calls it with the specified args'''
		method = self.findmethod(rpcrequest.method)
		if method is None: raise MethodNotFound

		return method(*rpcrequest.args, **rpcrequest.kwargs)

	def findmethod(self, method):
		'''Override to allow server to define methods'''
		return lambda *a, **kw: 'Test Data'

	def processrequest(self, result, args):
		'''Override to implement custom handling of the method result and request'''
		return result

	def log(self, result, request):
		'''Override to implement custom error handling'''
		pass

	def processcontent(self, content, request):
		'''Given the freshly decoded content of the request, return what content should be used'''
		return content


@public
class ServerError(Exception):
	'''Base Exception for JSON-RPC Errors, if this or a subclass of this is raised by a JSON-RPC method,
	The server will convert it into an appropriate error object
	'''

	#: Error code
	code = 0
	#: Error message
	msg = ""

	def json_equivalent(self):
		'''return a dictionary which matches an JSON-RPC Response'''
		return dict(code=self.code, message=self.msg)

	def __str__(self):
		return jsonrpc.jsonutil.encode(self)

@public
class InvalidRequest(ServerError):
	'''Raise this when the Request object does not match the schema'''
	code = -32600
	msg = "Invalid Request."

@public
class MethodNotFound(ServerError):
	'''Raise this when the desired method is not found'''
	code = -32601
	msg = "Procedure not found."

@public
class ParseError(ServerError):
	'''Raise this when the request contains invalid JSON'''
	code = -32700
	msg = "Parse error."

class Request(object):
	def __init__(self, content):
		self.version = content.get('jsonrpc')
		self.id = content.get('id')

		self.method = content.get('method')

		kwargs = content.get('params', {})
		args = ()
		if not isinstance(kwargs, dict):
			args = tuple(kwargs)
			kwargs = {}
		else:
			args = kwargs.pop('__args', args)

		self.args = args
		self.kwargs = dict( (str(k), v) for k,v in kwargs.items() )

	def check(self):
		if self.version != '2.0': raise InvalidRequest
		if not isinstance(self.method, (str, unicode)): raise InvalidRequest

	@classmethod
	def from_list(cls, content):
		result = []
		for req in content:
			result.append(cls(req))
		return result


class Response(object):
	def __init__(self, id=None, result=None, error=None):
		self.version = '2.0'
		self.id = id
		self.result = result
		self.error = error

	def json_equivalent(self):
		res = dict(jsonrpc=self.version, id=self.id)
		if self.error is None:
			res['result'] = self.result
		else:
			res['error'] = self.error
		return res


## Base class providing a JSON-RPC 2.0 implementation with 2 customizable hooks
@public
class JSON_RPC(Resource):
	'''This class implements a JSON-RPC 2.0 server as a Twisted Resource'''
	isLeaf = True

	#: set by :py:meth:`customize` used to change the behavior of the server
	eventhandler = ServerEvents

	def customize(self, eventhandler):
		'''customize the behavior of the server'''
		self.eventhandler = eventhandler(self)
		return self


	def __init__(self, *args, **kwargs):
		self.customize(self.eventhandler)
		Resource.__init__(self,*args, **kwargs)


	def render(self, request):
		#move to emen2 event handler
		#ctxid = request.getCookie("ctxid") or request.args.get("ctxid", [None])[0]
		#host = request.getClientIP()

		request.content.seek(0, 0)
		try:
			try:
				content = jsonrpc.jsonutil.decode(request.content.read())
			except ValueError: raise ParseError

			content = self.eventhandler.processcontent(content, request)

			if isinstance(content, list):
				content = Request.from_list(content)
			else:
				content = Request(content)

			try:
				if hasattr(content, 'check'):
					content.check()
				else:
					for item in content: item.check()

			except ServerError, e:
				self._ebRender(e, request, content.id if hasattr(content, 'id') else None)

			d = threads.deferToThread(self._action, request, content)
			d.addCallback(self._cbRender, request)
			d.addErrback(self._ebRender, request, content.id if hasattr(content, 'id') else None)
		except BaseException, e:
			self._ebRender(e, request, None)

		return server.NOT_DONE_YET

	def _action(self, request, contents):
		result = []

		islist = (True if isinstance(contents, list) else False)
		if not islist: contents = [contents]

		if contents == []: raise InvalidRequest

		for rpcrequest in contents:
			res = None

			try:
				res = Response(id=rpcrequest.id, result=self.eventhandler.callmethod(request, rpcrequest))
				res = self.eventhandler.processrequest(res, request.args)
			except Exception, e:
				res = self.render_error(e, rpcrequest.id)

			if res.id is not None:
				result.append(res)


		self.eventhandler.log(result, request)

		if result != []:
			if not islist: result = result[0]
		else: result = None

		return result



	def _cbRender(self, result, request):
		if result is not None:
			request.setHeader("content-type", 'application/json')
			request.setResponseCode(200)
			result = jsonrpc.jsonutil.encode(result).encode('utf-8')
			request.setHeader("content-length", len(result))
			request.write(result)
		request.finish()

	def _ebRender(self, result, request, id, finish=True):
		self.eventhandler.log(result, request)

		err = None
		if not isinstance(result, BaseException):
			try: result.raiseException()
			except BaseException, e:
				err = e
		else: err = result
		err = self.render_error(err, id)

		request.setHeader("content-type", 'application/json')
		request.setResponseCode(200)
		result = jsonrpc.jsonutil.encode(err).encode('utf-8')
		request.setHeader("content-length", len(result))
		request.write(result)
		if finish: request.finish()


	def render_error(self, e, id):
		if isinstance(e, ServerError):
			err = Response(id=id, error=e)
		else:
			err = Response(id=id, error=dict(code=0, message=str(e), data=e.args))

		return err





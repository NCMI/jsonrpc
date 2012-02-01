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
import traceback
import jsonrpc.jsonutil
from jsonrpc.utilities import public
import jsonrpc.common

# Twisted imports
from twisted.web import server
from twisted.internet import threads
from twisted.internet import defer
from twisted.web.resource import Resource

import abc

import copy
import UserDict, collections
collections.Mapping.register(UserDict.DictMixin)

@public
class ServerEvents(object):
	'''Subclass this and pass to :py:meth:`JSON_RPC.customize` to customize the JSON-RPC server'''

	DEBUG = False

	#: an object defining a 'get' method which contains the methods
	methods = None

	def __init__(self, server):
		#: A link to the JSON-RPC server instance
		self.server = server

	def callmethod(self, txrequest, rpcrequest, **extra):
		'''Find the method and call it with the specified args

		:returns: the result of the method'''

		extra.update(rpcrequest.kwargs)

		method, postprocess_result = self.findmethod(rpcrequest.method, rpcrequest.args, extra), False
		if hasattr('method', '__iter__'):
			method, postprocess_result = method

		if self.DEBUG:
			# Debugging: raise AssertionError if type of method is invalid
			assert method is None or callable(method), 'the returned method is not callable'

		if not callable(method): raise jsonrpc.common.MethodNotFound

		result = method(*rpcrequest.args, **extra)

		#if the result needs to be adjusted/validated, do it
		if postprocess_result:
			result = self.methods.postprocess(rpcrequest.method, result, rpcrequest.args, extra)

		return result

	def findmethod(self, method_name, args=None, kwargs=None):
		'''Return the callable associated with the method name

		:returns: a callable or None if the method is not found'''
		if self.methods is not None:
			return self.methods.get(method_name)
		else:
			raise NotImplementedError

	def processrequest(self, result, args, **kw):
		'''Override to implement custom handling of the method result and request'''
		return result

	def log(self, response, txrequest, error=False):
		'''Override to implement custom logging'''
		pass

	def processcontent(self, content, request):
		'''Given the freshly decoded content of the request, return the content that should be used

		:returns: an object which implements the :py:class:`collections.MutableMapping` interface'''
		return content

	def getresponsecode(self, result):
		'''Take the result, and return an appropriate HTTP response code, returns 200 by default

		NOTE: if an error code is returned, the client error messages will be much less helpful!

		for example

			def getresponsecode(self, result):
				code = 200
				if not isinstance(result, list):
					if result is not None and result.error is not None:
						code = result.error.code or 500
				return code


		:returns: :py:class:`int`'''
		# returns 200 so that the python client can see something useful
		return 200

	def defer(self, method, *a, **kw):
		'''Defer to thread. Override this method if you are using a different ThreadPool, or if you want to return immediately.

		:returns: :py:class:`twisted.internet.defer.Deferred`'''
		return threads.deferToThread(method, *a, **kw)

	def defer_with_rpcrequest(self, method, rpcrequest, *a, **kw):
		d = self.defer(method, rpcrequest, *a, **kw)

		@d.addCallback
		def _inner(result):
			return result, rpcrequest
		@d.addErrback
		def _inner(result):
			result.rpcrequest = rpcrequest
			return result

		return d



## Base class providing a JSON-RPC 2.0 implementation with 2 customizable hooks
@public
class JSON_RPC(Resource):
	'''This class implements a JSON-RPC 2.0 server as a Twisted Resource'''
	isLeaf = True

	### NOTE: these comments are used by Sphinx as documentation.
	#: An instance of :py:class:`ServerEvents` which supplies callbacks to
	#: customize the operation of the server.  The proper way to initialize this
	#: is either to subclass and set it manually, or, preferably, to call :py:meth:`customize`.
	eventhandler = ServerEvents

	def customize(self, eventhandler):
		'''customize the behavior of the server'''
		self.eventhandler = eventhandler(self)
		return self


	def __init__(self, *args, **kwargs):
		self.customize(self.eventhandler)
		Resource.__init__(self,*args, **kwargs)


	def render(self, request):
		result = ''
		request.content.seek(0, 0)
		try:
			try:
				content = jsonrpc.jsonutil.decode(request.content.read())
			except ValueError:
				self.eventhandler.log(None, request, True)
				raise jsonrpc.common.ParseError

			content = self.eventhandler.processcontent(content, request)

			content = jsonrpc.common.Request.from_json(content)

			try:
				if hasattr(content, 'check'):
					content.check()
				else:
					for item in content: item.check()

			except jsonrpc.common.RPCError, e:
				self._ebRender(e, request, content.id if hasattr(content, 'id') else None)

			else:
				d = self._action(request, content)
				d.addCallback(self._cbRender, request)
				d.addErrback(self._ebRender, request, content.id if hasattr(content, 'id') else None)
		except BaseException, e:
			self._ebRender(e, request, None)

		return server.NOT_DONE_YET



	def _action(self, request, contents, **kw):
		result = []

		islist = (True if isinstance(contents, list) else False)
		if not islist: contents = [contents]

		if contents == []: raise jsonrpc.common.InvalidRequest

		def callmethod(rpcrequest, request, add, **kwargs):
			print 'jsonrpc.server callmethod: %s, %s, %s, %s' % (rpcrequest, request, add, kwargs)
			add.update(kwargs)
			result = self.eventhandler.callmethod(request, rpcrequest, **add)
			return result

		deferreds = []
		for rpcrequest in contents:
			res = None
			add = copy.deepcopy(rpcrequest.extra)
			add.update(kw)
			deferreds.append(self.eventhandler.defer_with_rpcrequest(callmethod, rpcrequest, request, add))
		deferreds = defer.DeferredList(deferreds, consumeErrors=True)

		@deferreds.addCallback
		def helper(deferredresults):
			result = []
			try:
				for success, methodresult in deferredresults:
					res = None
					if success:
						methodresult, rpcrequest = methodresult
						res = jsonrpc.common.Response(id=rpcrequest.id, result=methodresult)
						res = self.eventhandler.processrequest(res, request.args, **kw)
					else:
						rpcrequest = methodresult.rpcrequest
						try:
							methodresult.raiseException()
						except Exception, e:
							res = self.render_error(e, rpcrequest.id)
							self.eventhandler.log(res, request, error=True)

					if res.id is not None:
						result.append(res)
			except Exception, e:
				traceback.print_exc()
				raise

			if result != []:
				if not islist: result = result[0]
			else: result = None
			return result

		return deferreds


	def _cbRender(self, result, request):
		@self.eventhandler.defer
		def _inner(*args, **_):
			code = self.eventhandler.getresponsecode(result)
			request.setResponseCode(code)
			self.eventhandler.log(result, request, error=False)
			if result is not None:
				request.setHeader("content-type", 'application/json')
				result_ = jsonrpc.jsonutil.encode(result).encode('utf-8')
				request.setHeader("content-length", len(result_))
				request.write(result_)
			request.finish()
		return _inner

	def _ebRender(self, result, request, id, finish=True):
		@self.eventhandler.defer
		def _inner(*args, **_):
			err = None
			if not isinstance(result, BaseException):
				try: result.raiseException()
				except BaseException, e:
					err = e
					self.eventhandler.log(err, request, error=True)
			else: err = result
			err = self.render_error(err, id)

			code = self.eventhandler.getresponsecode(result)
			request.setResponseCode(code)

			request.setHeader("content-type", 'application/json')
			result_ = jsonrpc.jsonutil.encode(err).encode('utf-8')
			request.setHeader("content-length", len(result_))
			request.write(result_)
			if finish: request.finish()
		return _inner

	def render_error(self, e, id):
		if isinstance(e, jsonrpc.common.RPCError):
			err = jsonrpc.common.Response(id=id, error=e)
		else:
			err = jsonrpc.common.Response(id=id, error=dict(code=0, message=str(e), data=e.args))

		return err





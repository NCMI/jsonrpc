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
import jsonrpc.common

# Twisted imports
from twisted.web import server
from twisted.internet import threads
from twisted.web.resource import Resource


import copy
import UserDict, collections
collections.Mapping.register(UserDict.DictMixin)

@public
class ServerEvents(object):
	'''Subclass this and pass to :py:meth:`jsonrpc.customize` to customize the jsonrpc server'''

	def __init__(self, server):
		#: A link to the JSON-RPC server instance
		self.server = server

	def callmethod(self, txrequest, rpcrequest, **extra):
		'''Finds the method and calls it with the specified args'''
		method = self.findmethod(rpcrequest.method)
		if method is None: raise jsonrpc.common.MethodNotFound
		extra.update(rpcrequest.kwargs)

		return method(*rpcrequest.args, **extra)

	def findmethod(self, method):
		'''Override to allow server to define methods'''
		return lambda *a, **kw: 'Test Data'

	def processrequest(self, result, args, **kw):
		'''Override to implement custom handling of the method result and request'''
		return result

	def log(self, response, txrequest):
		'''Override to implement custom error handling'''
		pass

	def processcontent(self, content, request):
		'''Given the freshly decoded content of the request, return what content should be used'''
		return content



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
		request.content.seek(0, 0)
		try:
			try:
				content = jsonrpc.jsonutil.decode(request.content.read())
			except ValueError: raise jsonrpc.common.ParseError

			content = self.eventhandler.processcontent(content, request)

			if isinstance(content, list):
				content = jsonrpc.common.Request.from_list(content)
			else:
				content = jsonrpc.common.Request.from_dict(content)

			try:
				if hasattr(content, 'check'):
					content.check()
				else:
					for item in content: item.check()

			except jsonrpc.common.RPCError, e:
				self._ebRender(e, request, content.id if hasattr(content, 'id') else None)

			d = threads.deferToThread(self._action, request, content)
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

		for rpcrequest in contents:
			res = None

			try:
				add = copy.deepcopy(rpcrequest.extra)
				add.update(kw)
				res = jsonrpc.common.Response(id=rpcrequest.id, result=self.eventhandler.callmethod(request, rpcrequest, **add))
				res = self.eventhandler.processrequest(res, request.args, **kw)
			except Exception, e:
				res = self.render_error(e, rpcrequest.id)

			if res.id is not None:
				result.append(res)



		if result != []:
			if not islist: result = result[0]
		else: result = None

		self.eventhandler.log(result, request)
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

		err = None
		if not isinstance(result, BaseException):
			try: result.raiseException()
			except BaseException, e:
				err = e
		else: err = result
		err = self.render_error(err, id)
		self.eventhandler.log(err, request)

		request.setHeader("content-type", 'application/json')
		request.setResponseCode(200)
		result = jsonrpc.jsonutil.encode(err).encode('utf-8')
		request.setHeader("content-length", len(result))
		request.write(result)
		if finish: request.finish()


	def render_error(self, e, id):
		if isinstance(e, jsonrpc.common.RPCError):
			err = jsonrpc.common.Response(id=id, error=e)
		else:
			err = jsonrpc.common.Response(id=id, error=dict(code=0, message=str(e), data=e.args))

		return err





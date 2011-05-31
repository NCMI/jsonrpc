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
import cgi
import copy
import time
import itertools
import jsonrpc.jsonutil

# Twisted imports
from twisted.web import server
from twisted.internet import threads
from twisted.web.resource import Resource


import UserDict, collections
collections.Mapping.register(UserDict.DictMixin)

class ServerEvents(object):
	'''Subclass this and pass to :py:meth:`jsonrpc.customize` to customize the jsonrpc server'''

	def __init__(self, jsonrpc):
		#: A link to the JSON-RPC server instance
		self.server = jsonrpc

	def callmethod(self, request, method, kwargs, args, **kw):
		'''Override to implement the methods the server will make available'''
		return 'Test Result'

	def processrequest(self, result, args):
		'''Override to implement custom handling of the method result and request'''
		return result

	def log(self, result, request):
		'''Override to implement custom error handling'''
		pass




## Base class providing a JSON-RPC 2.0 implementation with 2 customizable hooks
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

	def _parse_data(self, content):
		if content.get('jsonrpc') != '2.0': raise ValueError, 'wrong JSON-RPC version'
		method = content.get('method')
		kwargs = content.get('params', {})
		args = ()
		if not isinstance(kwargs, dict):
			args = tuple(kwargs)
			kwargs = {}
		else:
			args = kwargs.pop('__args', args)
		kwargs = dict( (str(k), v) for k,v in kwargs.items() )
		return method, kwargs, args


	def _cbRender(self, result, request):
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


	def get_result(method_result, content, template):
		template['error'].update(
				code=0,
				message=cgi.escape(' '.join(str(x) for x in method_result.value)),
				data=content
		)
		template['id'] = content.get(id)
		return template



	def render(self, request):
		ctxid = request.getCookie("ctxid") or request.args.get("ctxid", [None])[0]
		host = request.getClientIP()

		request.content.seek(0, 0)
		try:
			content = jsonrpc.jsonutil.decode(request.content.read())
			d = threads.deferToThread(self._action, request, content, ctxid=ctxid, host=host)
			d.addCallback(self._cbRender, request)
			d.addErrback(self._ebRender, request, content.get('id') if hasattr(content, 'get') else None)
		except BaseException, e:
			self._ebRender(e, request, None)

		return server.NOT_DONE_YET

	def render_error(self, e, id):
		err = dict(
			jsonrpc='2.0',
			id = id,
			error= dict(
				code=0,
				message=str(e),
				data = e.args
		))
		return err



	def _action(self, request, contents, **kw):
		result = []
		ol = (True if isinstance(contents, list) else False)
		if not ol:
			contents = [contents]

		for content in contents:
			try:
				res = dict(
					jsonrpc = '2.0',
					id = content.get('id'),
					result = self.eventhandler.callmethod(request, *self._parse_data(content), **kw)
				)

				res = self.eventhandler.processrequest(res, request.args)

				result.append(res)
			except Exception, e:
				err = self.render_error(e, content.get('id'))
				result.append(err)


		self.eventhandler.log(result, request)

		return ( result if ol else result[0] )



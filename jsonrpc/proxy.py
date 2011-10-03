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
import copy
import cookielib
import urllib2
import urlparse
import itertools
import traceback
import random
import time
import UserDict, collections
collections.Mapping.register(UserDict.DictMixin)

from hashlib import sha1
import jsonrpc.jsonutil
from jsonrpc.common import Response, Request

__all__ = ['JSONRPCProxy', 'ProxyEvents']

class NewStyleBaseException(Exception):
    def _get_message(self):
        return self._message
    def _set_message(self, message):
        self._message = message

    message = property(_get_message, _set_message)


class IDGen(object):
	def __init__(self):
		self._hasher = sha1()
		self._id = 0
	def __get__(self, *_, **__):
		self._id += 1
		self._hasher.update(str(self._id))
		self._hasher.update(time.ctime())
		self._hasher.update(str(random.random))
		return self._hasher.hexdigest()



class ProxyEvents(object):
	'''An event handler for JSONRPCProxy'''

	#: an instance of a class which defines a __get__ method, used to generate a request id
	IDGen = IDGen()


	def __init__(self, proxy):
		'''Allow a subclass to do its own initialization, gets any arguments leftover from __init__'''
		self.proxy = proxy

	def get_params(self, args, kwargs):
		'''allow a subclass to modify the method's arguments

		e.g. if an authentication token is necessary, the subclass can automatically insert it into every call'''
		return args, kwargs

	def proc_response(self, data):
		'''allow a subclass to access the response data before it is returned to the user'''
		return data

class JSONRPCProxy(object):
	'''A class implementing a JSON-RPC Proxy.

	:param str host: The HTTP server hosting the JSON-RPC server
	:param str path: The path where the JSON-RPC server can be found

	There are two ways of instantiating this class:
	- JSONRPCProxy.from_url(url) -- give the absolute url to the JSON-RPC server
	- JSONRPC(host, path) -- break up the url into smaller parts

	'''

	#: Override this attribute to customize proxy behavior
	_eventhandler = ProxyEvents
	def customize(self, eventhandler):
		self._eventhandler = eventhandler(self)
		return self

	def _transformURL(self, serviceURL, path):
		if serviceURL.endswith('/'):
			serviceURL = serviceURL[:-1]
		if path.endswith('/'):
			path = path[:-1]
		if path.startswith('/'):
			path = path[1:]
		return serviceURL, path


	## Public interface
	@classmethod
	def from_url(cls, url, ctxid=None, serviceName=None):
		'''Create a JSONRPCProxy from a URL'''
		urlsp = urlparse.urlsplit(url)
		url = '{0}://{1}'.format(urlsp.scheme, urlsp.netloc)
		path = urlsp.path
		if urlsp.query: path = '{0}?{1}'.format(path, urlsp.query)
		if urlsp.fragment: path = '{0}#{1}'.format(path, urlsp.fragment)
		return cls(url, path, serviceName, ctxid)


	def __init__(self, host, path='jsonrpc', serviceName=None, *args, **kwargs):
		self.serviceURL = host
		self._serviceName = serviceName
		self._path = path
		self.serviceURL, self._path = self._transformURL(host, path)
		self.customize(self._eventhandler)

		cj = cookielib.CookieJar()
		self._opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))



	def _set_opener(self, opener):
		self._opener  = opener
		return self

	def __getattr__(self, name):
		if self._serviceName != None:
			name = "{0}.{1}".format(self._serviceName, name)
		return self.__class__(self.serviceURL, path=self._path, serviceName=name).customize(type(self._eventhandler))._set_opener(self._opener)


	def _get_postdata(self, args=None, kwargs=None):
		_args, _kwargs = self._eventhandler.get_params(args, kwargs)
		id = self._eventhandler.IDGen
		result = Request(id, self._serviceName, _args, _kwargs)
		return jsonrpc.jsonutil.encode(result)

	def _get_url(self):
		result = [self.serviceURL]
		if self._path:
			result.append(self._path)
		#result.append('')
		return '/'.join(result)

	def _post(self, url, data):
		return self._opener.open(url, data)

	def __call__(self, *args, **kwargs):

		url = self._get_url()
		postdata = self._get_postdata(args, kwargs)
		#respdata = urllib2.urlopen(url, postdata).read()
		respdata = self._post(url, postdata).read()
		resp = Response.from_dict(jsonrpc.jsonutil.decode(respdata))
		resp = self._eventhandler.proc_response(resp)

		return resp.get_result()


	def call(self, method, *args, **kwargs):
		'''call a JSON-RPC method

		It's better to use instance.<methodname>(\\*args, \\*\\*kwargs),
		but this version might be useful occasionally
		'''
		p = self.__class__(self.serviceURL, path=self._path, serviceName=method)
		return p(*args, **kwargs)


	def batch_call(self, methods):
		'''call several methods at once, return a list of (result, error) pairs

		:param names: a dictionary { method: (args, kwargs) }
		:returns: a list of pairs (result, error) where only one is not None
		'''
		result = None
		if hasattr(methods, 'items'): methods = methods.items()
		data = [ getattr(self, k)._get_postdata(*v) for k, v in methods ]
		postdata = '{0}'.format(','.join(data))
		respdata = self._post(self._get_url(), postdata).read()
		resp = Response.from_json(respdata)
		try:
			result = resp.get_result()
		except AttributeError:
			result = [res.get_output() for res in resp]

		return result

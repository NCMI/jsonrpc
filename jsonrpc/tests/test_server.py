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
import functools
from twisted.trial import unittest
import StringIO

import mock

import jsonrpc.server
import jsonrpc.jsonutil

from twisted.web.test.test_web import DummyRequest
from twisted.internet.defer import succeed, DeferredList
from twisted.web.static import server

def _render(resource, request):
    result = resource.render(request)
    if isinstance(result, str):
        request.write(result)
        equest.finish()
        return succeed(None)
    elif result is server.NOT_DONE_YET:
        if request.finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise ValueError("Unexpected return value: %r" % (result,))

class SimpleEventHandler(jsonrpc.server.ServerEvents):
	def log(self, result, request, error=False): pass

	def findmethod(self, method, *_, **__):
		if method in set(['echo', 'add']):
			return getattr(self, method)

	def add(self, a,b):
		return a+b

	def echo(self, v): return v

def TestResource(setup):
	def _inner1(tests):
		@functools.wraps(setup)
		def _inner2(self):
			resource = jsonrpc.server.JSON_RPC()
			resource.customize(SimpleEventHandler)

			request = DummyRequest([''])
			request.getCookie = mock.Mock()

			result = setup(self, request, resource)
			if result is not None:
				request, resource = result

			d = _render(resource, request).addCallback(tests, self, request, resource)
			return d
		return _inner2
	return _inner1


class TestJSONRPCServer(unittest.TestCase):

	def setUp(self):
		self.id_ = 'an_id'
		self.param = "some data"

	@TestResource
	def test_eventhandler(self, request, resource):
		resource.eventhandler = mock.Mock(wraps=resource.eventhandler)
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))
		return request, resource

	@test_eventhandler
	def test_eventhandler(ignored, self, request, resource):
		self.assertTrue( resource.eventhandler.processcontent.called )
		self.assertTrue( resource.eventhandler.defer_with_rpcrequest.called )
		self.assertTrue( resource.eventhandler.callmethod.called )
		self.assertTrue( resource.eventhandler.defer.called )
		self.assertTrue( resource.eventhandler.getresponsecode.called )
		self.assertTrue( resource.eventhandler.log.called )

	@TestResource
	def test_requestid0(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))
		return request, resource

	@test_requestid0
	def test_requestid0(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data["id"], self.id_)


	@TestResource
	def test_requestid1(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": 1}' % jsonrpc.jsonutil.encode([self.param]))
		return request, resource

	@test_requestid1
	def test_requestid1(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data["id"], 1)


	@TestResource
	def test_requestid2(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": []}' % jsonrpc.jsonutil.encode([self.param]))
		return request, resource

	@test_requestid2
	def test_requestid2(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertNotEqual(data["id"], [])

	@TestResource
	def test_requestid3(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": {}}' % jsonrpc.jsonutil.encode([self.param]))
		return request, resource

	@test_requestid3
	def test_requestid3(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertNotEqual(data["id"], {})

	@TestResource
	def test_invalid_data(self, request, resource):
		request.content = StringIO.StringIO(' {"v": %s}, "method": "echo"}' % (jsonrpc.jsonutil.encode(self.param)))
		return request, resource

	@test_invalid_data
	def test_invalid_data(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error."}, "id": None})


	@TestResource
	def test_wrongversion(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.1", "params": %s, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))


	@test_wrongversion
	def rendered(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(data, {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": self.id_})


	@TestResource
	def test_invalidmethodname(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": 0, "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))


	@test_invalidmethodname
	def rendered(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(data, {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": self.id_})

	@TestResource
	def test_missingmethod(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "non_existent", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))


	@test_missingmethod
	def rendered(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(data, {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Procedure not found."}, "id": self.id_})



	@TestResource
	def test_simplecall(self):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))

	@test_simplecall
	def rendered(ignored):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data['id'], self.id_)
		self.assertEqual(data['result'], self.param)

	@TestResource
	def test_notify(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": {"v": %s}, "method": "echo"}' % (jsonrpc.jsonutil.encode(self.param)))

	@test_notify
	def test_notify(ignored, self, request, resource):
		self.assertEqual(len(request.written), 0)


	@TestResource
	def _test_kwcall(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": {"v": %s}, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode(self.param), self.id_))

	@_test_kwcall
	def test_kwcall_id(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data['id'], self.id_)

	@_test_kwcall
	def test_kwcall_result(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data['result'], self.param)

	@TestResource
	def test_err(self, request, resource):
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": [1, "sss"], "method": "add", "id": "%s"}' % self.id_)
		return request, resource

	@test_err
	def test_err(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)
		data = jsonrpc.jsonutil.decode(request.written[0])

		self.assertEqual(data['id'], self.id_)
		self.assertTrue(data.get('error', False))

	@TestResource
	def _test_batchcall(self, request, resource):
		request.content = StringIO.StringIO(
			'[{"jsonrpc": "2.0", "params": [1, 2], "method": "add", "id": "1"},'
				'{"jsonrpc": "2.0", "params": {"a": 3, "b": 2}, "method": "add", "id": "2"}]'
		)
		return request, resource

	@_test_batchcall
	def test_batchcall1(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)

	@_test_batchcall
	def test_batchcall2(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(len(data), 2)

	@_test_batchcall
	def test_batchcall3(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(set(x['result'] for x in data), set([3,5]))

	@_test_batchcall
	def test_batchcall4(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(set(x['id'] for x in data), set("12"))

	@_test_batchcall
	def test_batchcall5(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertFalse(any(x.get('error', False) for x in data))

	@TestResource
	def _test_batchcall_1err(self, request, resource):
		request.content = StringIO.StringIO(
			'[{"jsonrpc": "2.0", "params": [1, 2], "method": "add", "id": "1"},'
				'{"jsonrpc": "2.0", "params": {"a": "3", "b": 2}, "method": "add", "id": "2"}]'
		)
		return request, resource

	@_test_batchcall_1err
	def test_batchcall_1err_1(ignored, self, request, resource):
		self.assertEqual(len(request.written), 1)

	@_test_batchcall_1err
	def test_batchcall_1err_2(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(len(data), 2)

	@_test_batchcall_1err
	def test_batchcall_1err_3(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(set(x['id'] for x in data), set("12"))

	@_test_batchcall_1err
	def test_batchcall_1err_4(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(set(x.get('result', False) for x in data), set([3,False]))

	@_test_batchcall_1err
	def test_batchcall_1err_5(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(len(filter(None, [x.get('error') for x in data])), 1)


	@TestResource
	def _test_batchcall_emptylist(self, request, resource):
		request.content = StringIO.StringIO('[]')

	@_test_batchcall_emptylist
	def test_batchcall_emptylist(ignored, self, request, resource):
		data = jsonrpc.jsonutil.decode(request.written[0])
		self.assertEqual(data, {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": None})



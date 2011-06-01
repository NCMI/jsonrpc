from twisted.trial import unittest
import StringIO

import mock

import jsonrpc.server
import jsonrpc.jsonutil

from twisted.web.test.test_web import DummyRequest
from twisted.internet.defer import succeed
from twisted.web.static import server

def _render(resource, request):
    result = resource.render(request)
    if isinstance(result, str):
        request.write(result)
        request.finish()
        return succeed(None)
    elif result is server.NOT_DONE_YET:
        if request.finished:
            return succeed(None)
        else:
            return request.notifyFinish()
    else:
        raise ValueError("Unexpected return value: %r" % (result,))

class SimpleEventHandler(jsonrpc.server.ServerEvents):
	def log(self, result, request): pass

	def findmethod(self, method):
		if method in set(['echo', 'add']):
			return getattr(self, method)

	def add(self, a,b):
		return a+b

	def echo(self, v): return v


class TestJSONRPCServer(unittest.TestCase):

	def setUp(self):
		self.id_ = 'an_id'
		self.param = "some data"

	def test_invalid_data(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO(' {"v": %s}, "method": "echo"}' % (jsonrpc.jsonutil.encode(self.param)))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])

			assert data == {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error."}, "id": None}

		return d

	def test_wrongversion(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.1", "params": %s, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])
			assert data == {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": self.id_}
		return d


	def test_invalidmethodname(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": 0, "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])
			assert data == {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": self.id_}
		return d

	def test_missingmethod(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "non_existent", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])
			assert data == {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Procedure not found."}, "id": self.id_}
		return d



	def test_simplecall(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": %s, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode([self.param]), self.id_))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])

			assert data['id'] == self.id_
			assert data['result'] == self.param
		return d

	def test_notify(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": {"v": %s}, "method": "echo"}' % (jsonrpc.jsonutil.encode(self.param)))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 0

		return d


	def test_kwcall(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": {"v": %s}, "method": "echo", "id": "%s"}' % (jsonrpc.jsonutil.encode(self.param), self.id_))

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])

			assert data['id'] == self.id_
			assert data['result'] == self.param

		return d


	def test_err(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.getCookie = mock.Mock()
		request.content = StringIO.StringIO('{"jsonrpc": "2.0", "params": [1, "sss"], "method": "add", "id": "%s"}' % self.id_)

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored, *a):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])

			assert data['id'] == self.id_
			assert data.get('error', False)
		return rendered

	def test_batchcall(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.content = StringIO.StringIO(
			'[{"jsonrpc": "2.0", "params": [1, 2], "method": "add", "id": "1"},'
				'{"jsonrpc": "2.0", "params": {"a": 3, "b": 2}, "method": "add", "id": "2"}]'
		)
		request.getCookie = mock.Mock()

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored, *a):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])
			assert len(data) == 2
			assert set(x['id'] for x in data) == set("12")
			assert set(x['result'] for x in data) == set([3,5])

			assert not any(x.get('error', False) for x in data)
		return rendered

	def test_batchcall_1err(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])
		request.content = StringIO.StringIO(
			'[{"jsonrpc": "2.0", "params": [1, 2], "method": "add", "id": "1"},'
				'{"jsonrpc": "2.0", "params": {"a": "3", "b": 2}, "method": "add", "id": "2"}]'
		)
		request.getCookie = mock.Mock()

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored, *a):
			assert len(request.written) == 1
			data = jsonrpc.jsonutil.decode(request.written[0])
			assert len(data) == 2
			assert set(x['id'] for x in data) == set("12")
			assert set(x.get('result', False) for x in data) == set([3,False])

			assert len(filter(None, [x.get('error') for x in data])) == 1
		return rendered


	def test_batchcall_emptylist(self):
		resource = jsonrpc.server.JSON_RPC()
		resource.customize(SimpleEventHandler)

		request = DummyRequest([''])

		request.content = StringIO.StringIO('[]')
		request.getCookie = mock.Mock()

		d = _render(resource, request)

		@d.addCallback
		def rendered(ignored, *a):
			data = jsonrpc.jsonutil.decode(request.written[0])
			assert data == {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request."}, "id": None}
		return rendered



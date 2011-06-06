import jsonrpc.common
import jsonrpc.proxy
from twisted.trial import unittest
import mock
import urllib
import StringIO

# Run example server before tests

class TestJSONRPCProxy(unittest.TestCase):

	def setUp(self):
		self.proxy = jsonrpc.proxy.JSONRPCProxy('http://localhost:8007', path='aaa')

	def test_eventhandler(self):
		eventhandler = mock.MagicMock(spec=jsonrpc.proxy.ProxyEvents)
		args = (1,2)
		kwargs = {'a':1, 'b':2}

		def get_params(self, args, kwargs):
			print args, kwargs
			return args, kwargs
		eventhandler.get_params.side_effect = get_params

		eventhandler.proc_response.side_effect = lambda _, data: data

		self.proxy = jsonrpc.proxy.JSONRPCProxy.from_url('http://localhost:8007')
		self.proxy.customize(lambda *a: eventhandler)
		self.assertEqual(self.proxy._get_url(), 'http://localhost:8007/')

		self.proxy.add(*args)
		self.assertTrue(eventhandler.get_params.called)
		eventhandler.get_params.assert_called_once_with( args, {} )
		self.assertTrue(eventhandler.procresponse.called)

		eventhandler.reset_mock()

		self.proxy.add(**kwargs)
		self.assertTrue(eventhandler.get_params.called)
		eventhandler.get_params.assert_called_once_with( (), kwargs )
		self.assertTrue(eventhandler.procresponse.called)


	def test_url(self):
		self.proxy = jsonrpc.proxy.JSONRPCProxy.from_url('http://localhost:8007')
		self.assertEqual(self.proxy._get_url(), 'http://localhost:8007/')

		self.proxy = jsonrpc.proxy.JSONRPCProxy.from_url('http://localhost:8007/aaa/')
		self.assertEqual(self.proxy._get_url(), 'http://localhost:8007/aaa/')

		self.proxy = jsonrpc.proxy.JSONRPCProxy.from_url('http://localhost:8007/aaa')
		self.assertEqual(self.proxy._get_url(), 'http://localhost:8007/aaa/')

		self.proxy = jsonrpc.proxy.JSONRPCProxy('http://localhost:8007')
		self.assertEqual(self.proxy._get_url(), 'http://localhost:8007/jsonrpc/')

		self.proxy = jsonrpc.proxy.JSONRPCProxy('http://localhost:8007', path='aaa')
		self.assertEqual(self.proxy._get_url(), 'http://localhost:8007/aaa/')

	def test_call(self):
		self.assertEqual(self.proxy.add(1,2), 3)
		self.assertEqual(self.proxy.subtract(2,1), 1)

	def test_exceptions(self):
		self.assertRaises(jsonrpc.common.RPCError, self.proxy.add, 1,'2')
		self.assertRaises(jsonrpc.common.MethodNotFound, self.proxy.missingmethod)

	def test_batchcall(self):
		batch =[
			('add',      [ (1,2), {} ]),
			('subtract', [ (2,1), {} ]),
			('add',      [ (1,3), {} ])
		]
		self.assertEqual(self.proxy.batch_call(batch), [(3, None), (1, None), (4, None)])

		batch =[
			('add',			[ (),    dict(a=1,b=2) ]),
			('subtract',	[ (2,1), dict() ]),
			('add',			[ (1,3), dict() ])
		]
		self.assertEqual(self.proxy.batch_call(batch), [(3, None), (1, None), (4, None)])

		batch =[
			('add', 			[ (), dict(a=1,b=2) ]),
			('subtract', 	[ (), dict(a=2,b=1) ]),
			('add', 			[ (), dict(a=1,b=3) ])
		]
		self.assertEqual(self.proxy.batch_call(batch), [(3, None), (1, None), (4, None)])


	#def test_<testname here>(self):
	#	pass

if __name__ == '__main__':
	unittest.main()

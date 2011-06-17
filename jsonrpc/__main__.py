import json
from jsonrpc import proxy
import argparse

def main(host, path=None, args=None):
	proxy_ = proxy.JSONRPCProxy(host, path)
	return proxy_

def iterate(iter_):
	if not hasattr(iter_, 'next'): iter_ = iter(iter_)
	rollback = []
	try:
		while True:
			to_yield = None
			if rollback != []:
				to_yield = rollback.pop(0)
			else:
				to_yield = iter_.next()


			result = (yield to_yield)
			while result is not None:
				rollback.append(result)
				result = yield
	except StopIteration: raise

if __name__ == '__main__':
	import sys
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--path', dest='path', help='path to the JSON-RPC server', nargs='?', default='/jsonrpc')
	parser.add_argument('host', metavar='HOST')
	args = parser.parse_args(sys.argv[1:])

	print args
	server = main(args.host, args.path)

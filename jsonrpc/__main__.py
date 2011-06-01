from jsonrpc import proxy
import optparse

def main(host, path=None):
	proxy_ = proxy.JSONRPCProxy(host, path)
	return proxy_

if __name__ == '__main__':
	optionparser = optparse.OptionParser()
	optionparser.add_option('-p', '--path', dest='path', help='path to the JSON-RPC server', default='/jsonrpc')
	(options, args) = optionparser.parse_args()
	server = main(args[0], options.path)

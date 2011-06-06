from distutils.core import setup

VERSION = "0.99a01"
URLBASE = "https://github.com/NCMI/jsonrpc"
URLMAP = {
	"daily": "tarball/master"
}

if __name__ == "__main__":
	setup(
		name='jsonrpc',
		version=VERSION,
		description='A JSON-RPC 2.0 client-server library',
		author='Edward Langley',
		author_email='langleyedward@gmail.com',
		url='https://github.com/NCMI/jsonrpc',
		download_url="https://github.com/NCMI/jsonrpc/tarball/master",
		packages=[
			'jsonrpc'
			],
		scripts=[]
		)

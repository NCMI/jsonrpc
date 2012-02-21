from distutils.core import setup

VERSION = "1.2"
URLBASE = "https://github.com/NCMI/jsonrpc"
URLMAP = {
	"daily": "tarball/master",
	"0.99a01": "tarball/0.99a",
	"0.99a02": "tarball/0.99a02",
	"1.1": "tarball/1.1",
	"1.2": "tarball/1.2",
}

if __name__ == "__main__":
	setup(
		name='jsonrpc',
		version=VERSION,
		description='A JSON-RPC 2.0 client-server library',
		author='Edward Langley',
		author_email='langleyedward@gmail.com',
		url=URLBASE,
		download_url='/'.join([URLBASE, URLMAP.get(VERSION, URLMAP['daily'])]),
		packages=[
			'jsonrpc'
			],
		scripts=[],
		license= 'BSD 2.0',
		keywords = ['JSON', 'jsonrpc', 'rpc'],
		classifiers = [
			'Development Status :: 4 - Beta',
			'Environment :: Web Environment',
			'Framework :: Twisted',
			'Intended Audience :: Developers',
			'License :: OSI Approved :: BSD License',
			'Operating System :: OS Independent',
			'Programming Language :: Python :: 2.6',
			'Programming Language :: Python :: 2.7',
			'Topic :: Software Development :: Libraries :: Python Modules',
		]
		)

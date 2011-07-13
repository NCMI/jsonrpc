from __future__ import print_function
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

"""
This module is primarily a wrapper around simplejson in order to make
it behave like demjson

- If an object being encoded has a 'json_equivalent' attribute, that will be called to get a (more)
	serializable object

- if it has an 'items' method, it will be called
	- if it defines both items and iteritems, the second will be used)

- if it is iterable, it will be made into a list

- otherwise 'str' will be called on the object, and that result will be used
"""
__all__ = ['encode', 'decode']

import functools

try:
	import json
except ImportError:
	import simplejson as json


def dict_encode(obj):
	items = getattr(obj, 'iteritems', obj.items)
	return dict( (encode_(k),encode_(v)) for k,v in items() )

def list_encode(obj):
	return list(encode_(i) for i in obj)

def safe_encode(obj):
	'''Always return something, even if it is useless for serialization'''
	try: json.dumps(obj)
	except TypeError: obj = str(obj)
	return obj

def encode_(obj, **kw):
	obj = getattr(obj, 'json_equivalent', lambda: obj)()
	func = lambda x: x
	if hasattr(obj, 'items'):
		func = dict_encode
	elif hasattr(obj, '__iter__'):
		func = list_encode
	else:
		func = safe_encode
	return func(obj)


encode = functools.partial(json.dumps, default=encode_)
decode = json.loads

__version__ = "$Revision: 1.2 $".split(":")[1][:-1].strip()

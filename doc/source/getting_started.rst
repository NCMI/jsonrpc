.. Copyright (c) 2011 Edward Langley
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   
   Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
   
   Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
   
   Neither the name of the project's author nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.
   
   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
   FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
   HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
   TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
   PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
   LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
   NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 

Getting Started
===============
This code will create a server that logs all requests, and provides two methods to clients:
add and subtract:

.. literalinclude:: ../../jsonrpc/example_server.py
   :language: python
   :linenos:
   :tab-width: 2
   :lines: 2,3,34-

To use this server (which is included as jsonrpc.example_server), start it and the client in this way:

.. code-block:: console

   % python -m jsonrpc.example_server &

   % python -i -m jsonrpc.__main__ http://localhost:8007
   
.. code-block:: python

   >>> server.add(1,2)
   3
   >>> server.subtract(3,2)
   1
   >>> server.batch_call(dict(
   ...   add = ((3, 2), {} ),
   ...   subtract = ((), {'a': 3, 'b': 2})
   ... ))
   [(5, None), (1, None)]

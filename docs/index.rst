.. AdventureTrack documentation master file, created by
   sphinx-quickstart on Thu Mar 23 09:30:57 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

AdventureTrack docs
===================

Hi there, these are the AdventureTrack docs. It's built up out of a number of microservices running an *asyncio* event loop, communicating with other services using the [Autobahn](autobahn.ws) [WAMP](wamp.ws) framework. [Crossbar](crossbar.io) is used as a WAMP router for both backend and frontend.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   deploying
   messages

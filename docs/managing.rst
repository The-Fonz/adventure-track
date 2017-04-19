Managing
--------
All microservices run under *supervisor* which, in turn, is monitored by *systemd*. When debugging or diagnosing, use systemd to restart supervisor or crossbar if necessary (e.g. after updating ``/etc/environment``), and use supervisor to restart and monitor processes (their logs can be tailed from within supervisor).


Systemd daemon processes
========================

All daemon processes are started on boot. They are all managed by *systemd*, they are:

- *nginx* as reverse proxy and static content server
- *crossbar* WAMP router used by all internal services and browser client
- *supervisor* process manager for all microservices

Restart these with something like ``sudo systemctl restart nginx crossbar supervisor``.

Managing microservices with *supervisor*
========================================

*Supervisor* has a rich commandline interface, accessible with ``sudo supervisorctl``.

Once in the commandline interface, start, stop or restart any process with something like ``restart <processname>``.

When changing *supervisor* config, restart the affected processes with ``reread`` and ``update``.

Tail logs with ``tail -f atsite``.

Diagnosing
==========
To see output from the *nginx*, *crossbar* or *supervisor* processes, use *systemd*'s *journalctl*. Something like ``sudo journalctl -u nginx``.

Nginx access and error logs can be found in ``/var/log/nginx/``.

Microservice logs can be tailed with *supervisorctl*, or accessed in the ``/home/atuser`` folder.

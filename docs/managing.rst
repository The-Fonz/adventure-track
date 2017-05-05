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

Copying data between production and dev
=======================================
The database can easily be dumped and restored using something like:

- Get the db dump from server and save locally: ``ssh root@DOMAIN.COM 'su - postgres -c "pg_dump -Fc -d atsite"' > ./backup_folder/backup_name.pgdump``
- Drop within VM with something like ``su - postgres 'dropdb atsite'``
- Restore within VM with ``pg_restore -d atsite backup/file/path.pgdump``

Then media files can be copied with:

- Get direct ssh access to VM by copying the output of ``vagrant ssh-config <desired_hostname>`` to ``$HOME/.ssh/config``
- Then copy all media files with rsync by ssh-ing into the VM and sharing keys (-A option): ``ssh -A <desired_hostname> 'rsync -a root@DOMAIN.COM:/home/atuser/media/ /home/atuser/media'``

Dumping and importing the database can also be combined into one command by using the ``-A`` option on ``ssh`` (assuming that the server keys are stored on the host machine but we don't want to copy them to the VM).

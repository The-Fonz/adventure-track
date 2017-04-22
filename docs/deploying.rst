Deploying
---------

Ansible does most of the heavy lifting. Some tasks need to be done manually:

 - Create database tables by running ``python -m backend.messages.db --create`` and substitute *messages* for every other service that needs db tables created.
 - Set the Telegram bot key if necessary (see backend.telegrambot module).
 - Set the Sentry logging key (see below).


Sentry logging
==============
[Sentry](sentry.io) can be used to log errors in production. For the backend services to use Sentry, set the *AT_SENTRY_DSN* envvar. (E.g. in */etc/environment*, which gets loaded by *systemd* on *supervisor* startup.) For the frontend to use Sentry, set the *AT_SENTRY_DSN_PUBLIC* in the environment where the javascript gets bundled.

Vagrant
=======
The vagrantfile specifies root login, to avoid problems when provisioning with ansible. Depending on the box used, you might have to set ``PermitRootLogin yes`` in ``/etc/ssh/sshd_config``. Also, you might have to install Python 2.7 as Ansible requires it.

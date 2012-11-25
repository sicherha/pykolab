EXTRA_DIST = \
	kolabd.sysconfig \
	kolabd.systemd \
	kolabd.sysvinit \
	kolabd.tmpfiles.d.conf

kolabddir = $(pythondir)/kolabd
kolabd_PYTHON = $(wildcard *.py)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) \
		$(DESTDIR)/$(localstatedir)/run/kolabd

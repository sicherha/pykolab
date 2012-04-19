EXTRA_DIST = \
	kolabd.sysconfig \
	kolabd.systemd \
	kolabd.sysvinit

kolabddir = $(pythondir)/kolabd
kolabd_PYTHON = $(wildcard *.py)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) \
		$(DESTDIR)/$(localstatedir)/run/kolabd

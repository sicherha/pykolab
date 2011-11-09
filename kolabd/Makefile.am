EXTRA_DIST = kolabd.sysvinit

kolabddir = $(pythondir)/kolabd
kolabd_PYTHON = $(wildcard *.py)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir)
	$(INSTALL) -p -m 755 kolabd.py $(DESTDIR)/$(sbindir)/kolabd

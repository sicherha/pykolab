DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

EXTRA_DIST = \
	AUTHORS \
	COPYING \
	README

execdir = $(sbindir)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) $(DISTDIR)/$(bindir)
	$(INSTALL) -p 755 pykolab.py $(DESTDIR)/$(sbindir)
	pushd $(DESTDIR)$(bindir);$(LN_S) consolehelper pykolab;popd


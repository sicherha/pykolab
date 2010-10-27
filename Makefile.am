DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

EXTRA_DIST = \
	AUTHORS \
	ChangeLog \
	COPYING \
	INSTALL \
	NEWS \
	README \
	README.tests

execdir = $(sbindir)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) $(DISTDIR)/$(bindir)
	$(INSTALL) -p -m 755 pykolab.py $(DESTDIR)/$(sbindir)/pykolab
	pushd $(DESTDIR)$(bindir);$(LN_S) consolehelper pykolab;popd


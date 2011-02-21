DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

INTLTOOL_FILES = \
	intltool-extract.in \
	intltool-merge.in \
	intltool-update.in

PYTHON_FILES = \
	cyruslib.py

EXTRA_DIST = \
	AUTHORS \
	ChangeLog \
	COPYING \
	INSTALL \
	NEWS \
	README \
	README.tests \
	pykolab.spec \
	pykolab.spec.in \
	$(PYTHON_FILES)

SUBDIRS = \
	conf \
	kolab \
	kolabd \
	po \
	pykolab

ChangeLog:
	(GIT_DIR=.git git log > .changelog.tmp && mv .changelog.tmp ChangeLog; rm -f .changelog.tmp) || (touch ChangeLog; echo 'git directory not found: installing possibly empty changelog.' >&2)

srpm: ChangeLog dist
	@rpmbuild -ts $(PACKAGE)-$(VERSION).tar.gz

execdir = $(sbindir)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) $(DISTDIR)/$(bindir)
	$(INSTALL) -p -m 755 pykolab.py $(DESTDIR)/$(sbindir)/pykolab
	pushd $(DESTDIR)$(bindir);$(LN_S) consolehelper pykolab;popd


DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

INTLTOOL_FILES = \
	intltool-extract.in \
	intltool-merge.in \
	intltool-update.in

PYTHON_FILES = \
	cyruslib.py \
	conf.py \
	kolab.py \
	kolabd.py \
	kolabtest.py \
	setup-kolab.py

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
	pykolab \
	saslauthd

ChangeLog:
	(GIT_DIR=.git git log > .changelog.tmp && mv .changelog.tmp ChangeLog; rm -f .changelog.tmp) || (touch ChangeLog; echo 'git directory not found: installing possibly empty changelog.' >&2)

srpm: ChangeLog dist
	@rpmbuild -ts $(PACKAGE)-$(VERSION).tar.gz

execdir = $(sbindir)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) $(DESTDIR)/$(bindir)
	$(INSTALL) -p -m 755 conf.py $(DESTDIR)/$(sbindir)/kolab-conf
	$(INSTALL) -p -m 755 kolab.py $(DESTDIR)/$(sbindir)/kolab
	$(INSTALL) -p -m 755 kolabd.py $(DESTDIR)/$(sbindir)/kolabd
	$(INSTALL) -p -m 755 kolabtest.py $(DESTDIR)/$(bindir)/kolab-test
	$(INSTALL) -p -m 644 cyruslib.py $(DESTDIR)/$(datadir)/$(PACKAGE)/

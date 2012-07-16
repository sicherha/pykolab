DISTCLEANFILES = \
	intltool-extract \
	intltool-merge \
	intltool-update

INTLTOOL_FILES = \
	intltool-extract.in \
	intltool-merge.in \
	intltool-update.in

PYTHON_FILES = \
	bin/kolab_parse_telemetry.py \
	bin/kolab_smtp_access_policy.py \
	cyruslib.py \
	conf.py \
	kolab.py \
	kolabd.py \
	kolabtest.py \
	saslauthd.py \
	setup-kolab.py \
	wallace.py

EXTRA_DIST = \
	bin/rebuild.sh.in \
	AUTHORS \
	ChangeLog \
	COPYING \
	INSTALL \
	NEWS \
	README \
	README.tests \
	pykolab.spec \
	pykolab.spec.in \
	pylint.log \
	$(wildcard tests/*.py) \
	$(PYTHON_FILES)

SUBDIRS = \
	conf \
	kolab \
	kolabd \
	po \
	pykolab \
	saslauthd \
	share \
	wallace

ChangeLog: pylint
	(GIT_DIR=.git git log $(PACKAGE)-$(VERSION) > .changelog.tmp && mv .changelog.tmp ChangeLog; rm -f .changelog.tmp) || (touch ChangeLog; echo 'git directory not found: installing possibly empty changelog.' >&2)

pylint:
	@pylint \
		bin/kolab_smtp_access_policy.py \
		bin/kolab_parse_telemetry.py \
		bonnie.py \
		conf.py \
		kolabd.py \
		kolab.py \
		kolabtest.py \
		saslauthd.py \
		setup-kolab.py \
		wallace.py \
		bonnie/ \
		kolabd/ \
		kolab/ \
		pykolab/ \
		saslauthd/ \
		wallace/ \
		> pylint.log || :

srpm: ChangeLog dist 
	@rpmbuild -ts $(PACKAGE)-$(VERSION).tar.gz

rpm: srpm
	@rpmbuild -ta $(PACKAGE)-$(VERSION).tar.gz

binary:
	python ext/python/Tools/freeze/freeze.py \
		-p $(prefix) \
		-b $(libdir) \
		-x BaseHTTPServer \
		-x ConfigParser \
		-x FixTk \
		-x MySQLdb \
		-x SocketServer \
		-x StringIO \
		-x Tkconstants \
		-x Tkinter \
		-x UserDict \
		-x __future__ \
		-x _abcoll \
		-x _threading_local \
		-x _weakrefset \
		-x _xmlplus \
		-x abc \
		-x atexit \
		-x base64 \
		-x bdb \
		-x bisect \
		-x calendar \
		-x cmd \
		-x collections \
		-x copy \
		-x copy_reg \
		-x difflib \
		-x dis \
		-x distutils \
		-x doctest \
		-x dsml \
		-x dummy_thread \
		-x encodings \
		-x fnmatch \
		-x formatter \
		-x ftplib \
		-x functools \
		-x genericpath \
		-x getopt \
		-x getpass \
		-x gettext \
		-x glob \
		-x gzip \
		-x hashlib \
		-x hmac \
		-x httplib \
		-x imaplib \
		-x inspect \
		-x io \
		-x ldapurl \
		-x ldif \
		-x linecache \
		-x locale \
		-x logging \
		-x mimetools \
		-x mimetypes \
		-x ntpath \
		-x nturl2path \
		-x optparse \
		-x os2emxpath \
		-x pdb \
		-x pickle \
		-x pkgutil \
		-x posixpath \
		-x pprint \
		-x py_compile \
		-x pydoc \
		-x pydoc_data \
		-x quopri \
		-x random \
		-x repr \
		-x rfc822 \
		-x shlex \
		-x shutil \
		-x site \
		-x smtplib \
		-x socket \
		-x ssl \
		-x stat \
		-x string \
		-x struct \
		-x subprocess \
		-x sysconfig \
		-x tarfile \
		-x tempfile \
		-x textwrap \
		-x threading \
		-x traceback \
		-x types \
		-x urlparse \
		-x uu \
		-x warnings \
		-o src/kolabd/ \
		kolabd.py
	cd src/kolabd/; $(MAKE)

check:
	nosetests -v tests/

clean:
	rm -rf src/*; mkdir -p src/
	find -type f -name "*.pyo" -o -name "*.pyc" -delete

execdir = $(sbindir)

install-exec-local:
	mkdir -p $(DESTDIR)/$(sbindir) \
		$(DESTDIR)/$(bindir) \
		$(DESTDIR)/$(sysconfdir)/kolab \
		$(DESTDIR)/$(libexecdir)/postfix \
		$(DESTDIR)/$(localstatedir)/lib/kolab \
		$(DESTDIR)/$(localstatedir)/log/kolab \
		$(DESTDIR)/$(localstatedir)/spool/pykolab/wallace

if ENTERPRISE
	mkdir -p $(DESTDIR)/$(sysconfdir)/kolab/entitlement.d
endif
	$(INSTALL) -p -m 755 conf.py $(DESTDIR)/$(sbindir)/kolab-conf
	$(INSTALL) -p -m 755 kolab.py $(DESTDIR)/$(sbindir)/kolab
	$(INSTALL) -p -m 755 kolabd.py $(DESTDIR)/$(sbindir)/kolabd
	$(INSTALL) -p -m 755 saslauthd.py $(DESTDIR)/$(sbindir)/kolab-saslauthd
	$(INSTALL) -p -m 755 wallace.py $(DESTDIR)/$(sbindir)/wallaced
	$(INSTALL) -p -m 755 kolabtest.py $(DESTDIR)/$(bindir)/kolab-test
	$(INSTALL) -p -m 755 setup-kolab.py $(DESTDIR)/$(sbindir)/setup-kolab
	$(INSTALL) -p -m 644 cyruslib.py $(DESTDIR)/$(pythondir)
	$(INSTALL) -p -m 755 bin/kolab_parse_telemetry.py $(DESTDIR)/$(sbindir)/kolab_parse_telemetry
	$(INSTALL) -p -m 755 bin/kolab_smtp_access_policy.py $(DESTDIR)/$(libexecdir)/postfix/kolab_smtp_access_policy

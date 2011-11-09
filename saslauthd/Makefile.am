EXTRA_DIST = \
	kolab-saslauthd.sysconfig \
	kolab-saslauthd.sysvinit

saslauthddir = $(pythondir)/saslauthd
saslauthd_PYTHON = $(wildcard *.py)

install-exec-local:
	mkdir -p $(DESTDIR)/$(localstatedir)/run/kolab-saslauthd \
		$(DESTDIR)/$(localstatedir)/run/saslauthd \
		$(DESTDIR)/$(localstatedir)/lib/kolab-saslauthd



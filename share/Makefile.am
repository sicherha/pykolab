templatedir = $(datadir)/kolab/templates
template_DATA = \
	$(wildcard templates/*.tpl)

rctemplatedir = $(datadir)/kolab/templates/roundcubemail
rctemplate_DATA = \
	$(wildcard templates/roundcubemail/*.tpl)

EXTRA_DIST = \
	$(template_DATA) \
	$(rctemplate_DATA)

install-exec-local:
	mkdir -p \
		$(DESTDIR)/$(sysconfdir)/kolab/templates \
		$(DESTDIR)/$(sysconfdir)/kolab/templates/roundcubemail


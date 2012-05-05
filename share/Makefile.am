templatedir = $(datadir)/kolab/templates

template_DATA = \
	$(wildcard templates/*.tpl)

hordetemplatedir = $(datadir)/kolab/templates/horde/conf.d/
hordetemplate_DATA = \
	$(wildcard templates/horde/conf.d/*.tpl)

rctemplatedir = $(datadir)/kolab/templates/roundcubemail
rctemplate_DATA = \
	$(wildcard templates/roundcubemail/*.tpl)

zpushtemplatedir = $(datadir)/kolab/templates/zpush
zpushtemplate_DATA = \
	$(wildcard templates/zpush/*.tpl)

EXTRA_DIST = \
	$(template_DATA) \
	$(hordetemplate_DATA) \
	$(rctemplate_DATA) \
	$(zpushtemplate_DATA)

install-exec-local:
	mkdir -p \
		$(DESTDIR)/$(sysconfdir)/kolab/templates \
		$(DESTDIR)/$(sysconfdir)/kolab/templates/horde/conf.d \
		$(DESTDIR)/$(sysconfdir)/kolab/templates/roundcubemail \
		$(DESTDIR)/$(sysconfdir)/kolab/templates/zpush


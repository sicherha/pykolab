pykolabdir = $(pythondir)/$(PACKAGE)
pykolab_PYTHON = $(wildcard *.py)

pykolab_authdir = $(pythondir)/$(PACKAGE)/auth
pykolab_auth_PYTHON = \
	auth/__init__.py

pykolab_auth_ldapdir = $(pythondir)/$(PACKAGE)/auth/ldap
pykolab_auth_ldap_PYTHON = \
	auth/ldap/__init__.py \
	auth/ldap/cache.py \
	auth/ldap/syncrepl.py

pykolab_clidir = $(pythondir)/$(PACKAGE)/cli
pykolab_cli_PYTHON = \
	$(wildcard cli/*.py)

pykolab_clisievedir = $(pythondir)/$(PACKAGE)/cli/sieve
pykolab_clisieve_PYTHON = \
	$(wildcard cli/sieve/*.py)

pykolab_clitelemetrydir = $(pythondir)/$(PACKAGE)/cli/telemetry
pykolab_clitelemetry_PYTHON = \
	$(wildcard cli/telemetry/*.py)

pykolab_confdir = $(pythondir)/$(PACKAGE)/conf
pykolab_conf_PYTHON = \
	conf/defaults.py \
	conf/__init__.py

if ENTERPRISE
pykolab_conf_PYTHON += conf/entitlement.py
endif

pykolab_imapdir = $(pythondir)/$(PACKAGE)/imap
pykolab_imap_PYTHON = \
	imap/__init__.py \
	imap/cyrus.py

pykolab_pluginsdir = $(pythondir)/$(PACKAGE)/plugins
pykolab_plugins_PYTHON = \
	plugins/__init__.py

pykolab_plugins_defaultfoldersdir = $(pythondir)/$(PACKAGE)/plugins/defaultfolders
pykolab_plugins_defaultfolders_PYTHON = \
	plugins/defaultfolders/__init__.py

pykolab_plugins_dynamicquotadir = $(pythondir)/$(PACKAGE)/plugins/dynamicquota
pykolab_plugins_dynamicquota_PYTHON = \
	plugins/dynamicquota/__init__.py

pykolab_plugins_recipientpolicydir = $(pythondir)/$(PACKAGE)/plugins/recipientpolicy
pykolab_plugins_recipientpolicy_PYTHON = \
	plugins/recipientpolicy/__init__.py

pykolab_plugins_sievemgmtdir = $(pythondir)/$(PACKAGE)/plugins/sievemgmt
pykolab_plugins_sievemgmt_PYTHON = \
	plugins/sievemgmt/__init__.py

pykolab_setupdir = $(pythondir)/$(PACKAGE)/setup
pykolab_setup_PYTHON = \
	setup/components.py \
	setup/setup_freebusy.py \
	setup/setup_imap.py \
	setup/setup_kolabd.py \
	setup/setup_ldap.py \
	setup/setup_mta.py \
	setup/setup_mysql.py \
	setup/setup_php.py \
	setup/setup_roundcube.py \
	setup/setup_syncroton.py \
	setup/setup_zpush.py \
	setup/__init__.py

pykolab_wapclientdir = $(pythondir)/$(PACKAGE)/wap_client
pykolab_wapclient_PYTHON = \
	$(wildcard wap_client/*.py)

pykolab_xmldir = $(pythondir)/$(PACKAGE)/xml
pykolab_xml_PYTHON = \
	$(wildcard xml/*.py)

pykolabdir = $(pythondir)/$(PACKAGE)
pykolab_PYTHON = $(wildcard *.py)

pykolab_authdir = $(pythondir)/$(PACKAGE)/auth
pykolab_auth_PYTHON = \
	auth/__init__.py

pykolab_auth_ldapdir = $(pythondir)/$(PACKAGE)/auth/ldap
pykolab_auth_ldap_PYTHON = \
	auth/ldap/__init__.py \
	auth/ldap/cache.py

pykolab_clidir = $(pythondir)/$(PACKAGE)/cli
pykolab_cli_PYTHON = \
	$(wildcard cli/*.py)

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

pykolab_setupdir = $(pythondir)/$(PACKAGE)/setup
pykolab_setup_PYTHON = \
	setup/components.py \
	setup/setup_freebusy.py \
	setup/setup_imap.py \
	setup/setup_kolabd.py \
	setup/setup_ldap.py \
	setup/setup_mta.py \
	setup/setup_mysql.py \
	setup/setup_roundcube.py \
	setup/setup_zpush.py \
	setup/__init__.py

pykolab_testsdir = $(pythondir)/$(PACKAGE)/tests
pykolab_tests_PYTHON = \
	$(wildcard tests/*.py)

pykolab_tests_imapdir = $(pythondir)/$(PACKAGE)/tests/imap
pykolab_tests_imap_PYTHON = \
	$(wildcard tests/imap/*.py)

pykolab_tests_wapdir = $(pythondir)/$(PACKAGE)/tests/wap
pykolab_tests_wap_PYTHON = \
	$(wildcard tests/wap/*.py)


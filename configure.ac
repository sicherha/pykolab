AC_INIT([pykolab], 0.1)
AC_SUBST([RELEASE], 0.1)

AC_CONFIG_SRCDIR(pykolab/__init__.py.in)

ALL_LINGUAS="bn_IN bn ca cs da de el es fi fr gl gu hi hr hu is it ja ko ml ms nb nl or pa pl pt pt_BR ru sk sl sr@latin sr sv ta tr uk zh_CN zh_TW"

AM_INIT_AUTOMAKE
AM_MAINTAINER_MODE
AM_PATH_PYTHON

GETTEXT_PACKAGE=pykolab
AC_SUBST(GETTEXT_PACKAGE)
#AM_GLIB_GNU_GETTEXT
#AC_PROG_INTLTOOL
AC_PROG_LN_S

AC_SUBST(DATESTAMP,`date +"%a %b %d %Y"`)

AC_CONFIG_FILES([
Makefile
pykolab/constants.py
])

AC_OUTPUT

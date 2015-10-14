AC_INIT([pykolab], 0.7.16)
AC_SUBST([RELEASE], 1)

AC_CONFIG_SRCDIR(pykolab/constants.py.in)

ALL_LINGUAS="ach af af_ZA ak de de_DE es fr nl"

AM_INIT_AUTOMAKE
AM_MAINTAINER_MODE
AM_PATH_PYTHON

GETTEXT_PACKAGE=pykolab
AC_SUBST(GETTEXT_PACKAGE)
AM_GLIB_GNU_GETTEXT
AC_PROG_INTLTOOL
AC_PROG_LN_S

AC_ARG_ENABLE([enterprise],
    [  --enable-enterprise     Turn on entitlements, compile binary blob],
    [case "${enableval}" in
        yes)    enterprise=true ;;
        no)     enterprise=false ;;
        *)      AC_MSG_ERROR([bad value ${enableval} for --enterprise]) ;;
    esac], [enterprise=false])

AM_CONDITIONAL([ENTERPRISE], [test "${enterprise}" = "true"])

AC_SUBST(DATESTAMP,`date +"%a %b %d %Y"`)

AC_CONFIG_FILES([
bin/rebuild.sh
Makefile
pykolab.spec
conf/Makefile
kolabd/Makefile
po/Makefile.in
pykolab/constants.py
pykolab/Makefile
saslauthd/Makefile
share/Makefile
wallace/Makefile
])

AC_OUTPUT

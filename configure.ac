AC_INIT([pykolab], 0.5)
AC_SUBST([RELEASE], 0.16)

AC_CONFIG_SRCDIR(pykolab/constants.py.in)

ALL_LINGUAS="bn_IN bn ca cs da de el es fi fr gl gu hi hr hu is it ja ko ml ms nb nl or pa pl pt pt_BR ru sk sl sr@latin sr sv ta tr uk zh_CN zh_TW"

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
kolab/Makefile
kolabd/Makefile
po/Makefile.in
pykolab/constants.py
pykolab/Makefile
saslauthd/Makefile
share/Makefile
wallace/Makefile
])

AC_OUTPUT

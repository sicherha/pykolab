# standard standalone server implementation

START {
    # do not delete this entry!
    recover	    cmd="ctl_cyrusdb -r"

    idled       cmd="idled"
}

# UNIX sockets start with a slash and are put into /var/lib/imap/sockets
SERVICES {
    imaps       cmd="imapd -s"  listen="127.0.0.1:9993"                 prefork=5

    sieve       cmd="timsieved" listen="sieve"                          prefork=0

    ptloader    cmd="ptloader"  listen="/var/lib/imap/socket/ptsock"    prefork=0

    lmtpunix    cmd="lmtpd"     listen="/var/lib/imap/socket/lmtp"      prefork=1

    notify      cmd="notifyd"   listen="/var/lib/imap/socket/notify"    proto="udp" prefork=1
}

EVENTS {
    # this is required
    checkpoint	cmd="ctl_cyrusdb -c" period=30

    # this is only necessary if using duplicate delivery suppression,
    # Sieve or NNTP
    duplicateprune cmd="cyr_expire -E 3" at=0400

    # Expire data older then 69 days. Two full months of 31 days
    # each includes two full backup cycles, plus 1 week margin
    # because we run our full backups on the first sat/sun night
    # of each month.
    deleteprune cmd="cyr_expire -E 4 -D 69" at=0430
    expungeprune cmd="cyr_expire -E 4 -X 69" at=0445

    # this is only necessary if caching TLS sessions
    tlsprune	cmd="tls_prune" at=0400

    # Create search indexes regularly (remove -s for cyrus 3+)
    #squatter    cmd="squatter -s -i" at=0530
}

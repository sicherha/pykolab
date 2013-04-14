configdirectory: /var/lib/imap
partition-default: /var/spool/imap
admins: $admins
sievedir: /var/lib/imap/sieve
sendmail: /usr/sbin/sendmail
sasl_pwcheck_method: auxprop saslauthd
sasl_mech_list: PLAIN LOGIN
allowplaintext: no
tls_cert_file: /etc/pki/cyrus-imapd/cyrus-imapd.pem
tls_key_file: /etc/pki/cyrus-imapd/cyrus-imapd.pem
tls_ca_file: /etc/pki/tls/certs/ca-bundle.crt
# uncomment this if you're operating in a DSCP environment (RFC-4594)
# qosmarking: af13
auth_mech: pts
pts_module: ldap
ldap_servers: $ldap_servers
ldap_sasl: 0
ldap_base: $ldap_base
ldap_bind_dn: $ldap_bind_dn
ldap_password: $ldap_password
ldap_filter: $ldap_filter
ldap_user_attribute: $ldap_user_attribute
ldap_group_base: $ldap_group_base
ldap_group_filter: $ldap_group_filter
ldap_group_scope: $ldap_group_scope
ldap_member_base: $ldap_member_base
ldap_member_method: $ldap_member_method
ldap_member_attribute: $ldap_member_attribute
ldap_restart: 1
ldap_timeout: 10
ldap_time_limit: 10
unixhierarchysep: 1
virtdomains: userid
annotation_definitions: /etc/imapd.annotations.conf
sieve_extensions: fileinto reject envelope body vacation imapflags notify include regex subaddress relational copy
allowallsubscribe: 0
allowusermoves: 1
altnamespace: 1
hashimapspool: 1
anysievefolder: 1
fulldirhash: 0
sieveusehomedir: 0
sieve_allowreferrals: 0
lmtp_downcase_rcpt: 1
lmtp_fuzzy_mailbox_match: 1
username_tolower: 1
deletedprefix: DELETED
delete_mode: delayed
expunge_mode: delayed
flushseenstate: 1
postuser: shared

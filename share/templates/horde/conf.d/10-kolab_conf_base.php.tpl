<?php

\$conf['debug_level'] = E_ALL;

\$conf['tmpdir'] = '/var/lib/horde/tmp/';

\$conf['sql']['phptype'] = 'mysql';
\$conf['sql']['persistent'] = true;
\$conf['sql']['protocol'] = 'tcp';
\$conf['sql']['hostspec'] = 'localhost';
\$conf['sql']['username'] = 'roundcube';
\$conf['sql']['password'] = '$roundcube_mysql_password';
\$conf['sql']['database'] = 'roundcube';
\$conf['sql']['charset'] = 'utf-8';

\$conf['auth']['driver'] = 'kolab';
\$conf['auth']['params']['login_block'] = false;

\$conf['log']['priority'] = PEAR_LOG_DEBUG;
\$conf['log']['ident'] = 'HORDE';
\$conf['log']['params'] = array();
\$conf['log']['name'] = '/var/log/horde/horde.log';
\$conf['log']['params']['append'] = true;
\$conf['log']['type'] = 'file';
\$conf['log']['enabled'] = true;

\$conf['alarms']['driver'] = 'sql';
\$conf['prefs']['driver'] = 'sql';
\$conf['token']['driver'] = 'sql';
\$conf['vfs']['type'] = 'musql';

\$conf['perms']['driver'] = 'sql';

\$conf['group']['driver'] = 'kolab';
\$conf['group']['cache'] = true;
\$conf['share']['cache'] = true;
\$conf['share']['driver'] = 'kolab';

\$conf['cache']['default_lifetime'] = 1800;
\$conf['cache']['driver'] = 'memcache';

\$conf['mailer']['params']['host'] = 'localhost';
\$conf['mailer']['params']['port'] = 587;
\$conf['mailer']['params']['auth'] = true;
\$conf['mailer']['type'] = 'smtp';

\$conf['accounts']['driver'] = 'kolab';
\$conf['accounts']['params']['attr'] = 'mail';
\$conf['accounts']['params']['strip'] = false;

\$conf['kolab']['ldap']['server'] = 'localhost';
\$conf['kolab']['ldap']['basedn'] = '$ldap_base_dn';
\$conf['kolab']['ldap']['port'] = 389;
\$conf['kolab']['imap']['maildomain'] = '$primary_domain';
\$conf['kolab']['imap']['server'] = 'localhost';
\$conf['kolab']['imap']['port'] = 143;
\$conf['kolab']['imap']['protocol'] = "imap/tls/novalidate-cert";
\$conf['kolab']['imap']['sieveport'] = 4190;
\$conf['kolab']['imap']['cache_folders'] = true;
\$conf['kolab']['smtp']['server'] = 'localhost';
\$conf['kolab']['smtp']['port'] = 587;
\$conf['kolab']['misc']['multidomain'] = false;
\$conf['kolab']['cache_folders'] = true;
\$conf['kolab']['enabled'] = true;
\$conf['kolab']['freebusy']['server'] = 'https://' . \$_SERVER["HTTP_HOST"] . '/freebusy';


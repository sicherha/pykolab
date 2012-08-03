<?php
// Configuration for Kolab LDAP binding used by Kolab_Storage
\$rcmail_config['kolab']['ldap']['server'] = '$ldap_ldap_uri';
\$rcmail_config['kolab']['ldap']['basedn'] = '$ldap_base_dn';
\$rcmail_config['kolab']['ldap']['phpdn'] = '$ldap_service_bind_dn';
\$rcmail_config['kolab']['ldap']['phppw'] = '$ldap_service_bind_pw';

\$rcmail_config['kolab_freebusy_server'] = 'http://' . \$_SERVER["HTTP_HOST"] . '/freebusy';

\$rcmail_config['kolab']['imap']['secure'] = true;
\$rcmail_config['kolab']['imap']['namespaces'] = array(
    array('type' => 'personal', 'name' => '', 'delimiter' => '/'),
    array('type' => 'other', 'name' => 'Other Users', 'delimiter' => '/'),
    array('type' => 'shared', 'name' => 'Shared Folders', 'delimiter' => '/'),
);

?>

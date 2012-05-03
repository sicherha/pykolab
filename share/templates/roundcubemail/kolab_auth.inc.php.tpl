<?php

// The id of the LDAP address book (which refers to the rcmail_config['ldap_public'])
// or complete addressbook definition array.
\$rcmail_config['kolab_auth_addressbook'] = Array(
    'name'                      => 'Kolab Auth',
    'hosts'                     => Array('localhost'),
    'port'                      => 389,
    'use_tls'                   => false,
    'user_specific'             => false,
    'base_dn'                   => '$ldap_user_base_dn',
    'bind_dn'                   => '$ldap_service_bind_dn',
    'bind_pass'                 => '$ldap_service_bind_pw',
    'writable'                  => false,
    'ldap_version'              => 3,       // using LDAPv3
    'fieldmap'                  => Array(
            'name'              => 'displayname',
            'email'             => 'mail',
            'email:alias'       => 'alias',
            'role'              => 'nsroledn',
        ),
    'sort'                      => 'displayname',
    'scope'                     => 'sub',
    'filter'                    => '(objectClass=*)',
    'fuzzy_search'              => true,
    'sizelimit'                 => '0',
    'timelimit'                 => '0',
    'groups'                    => Array(
            'base_dn'           => '$ldap_group_base_dn',
            'filter'            => '$ldap_group_filter',
            'object_classes'    => Array('top', 'groupOfUniqueNames'),
            'member_attr'       => 'uniqueMember',
        ),
);


// This will overwrite defined filter
\$rcmail_config['kolab_auth_filter'] = '(&' . '$ldap_user_filter' . '(|(uid=%u)(mail=%fu)(alias=%fu)))';

// Use this fields (from fieldmap configuration) to get authentication ID
\$rcmail_config['kolab_auth_login'] = 'email';

// Use this fields (from fieldmap configuration) for default identity
\$rcmail_config['kolab_auth_name']  = 'name';
\$rcmail_config['kolab_auth_alias'] = 'alias';
\$rcmail_config['kolab_auth_email'] = 'email';

if (preg_match('/\/helpdesk-login\//', \$_SERVER["REQUEST_URI"]) ) {

    // Login and password of the admin user. Enables "Login As" feature.
    \$rcmail_config['kolab_auth_admin_login']    = '$imap_admin_login';
    \$rcmail_config['kolab_auth_admin_password'] = '$imap_admin_password';

    \$rcmail_config['kolab_auth_auditlog'] = true;
}

// Administrative role field (from fieldmap configuration) which must be filled with
// specified value which adds privilege to login as another user.
\$rcmail_config['kolab_auth_role']       = 'role';
\$rcmail_config['kolab_auth_role_value'] = 'cn=kolab-admin,$ldap_base_dn';

// Administrative group name to which user must be assigned to
// which adds privilege to login as another user.
\$rcmail_config['kolab_auth_group'] = 'Kolab Helpdesk';

?>

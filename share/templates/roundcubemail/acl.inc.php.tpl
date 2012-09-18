<?php
    \$rcmail_config['acl_advanced_mode'] = false;
    \$rcmail_config['acl_users_source'] = 'kolab_addressbook';
    \$rcmail_config['acl_users_field'] = 'mail';
    \$rcmail_config['acl_users_filter'] = 'objectClass=kolabInetOrgPerson';

    if (file_exists(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>

<?php

    \$rcmail_config = array();

    \$rcmail_config['db_dsnw'] = '$mysql_uri';

    if (file_exists(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__)) {
        include_once(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

    \$rcmail_config['db_max_length'] = 512000;
    \$rcmail_config['db_persistent'] = TRUE;
    \$rcmail_config['db_table_users'] = 'users';
    \$rcmail_config['db_table_identities'] = 'identities';
    \$rcmail_config['db_table_contacts'] = 'contacts';
    \$rcmail_config['db_table_contactgroups'] = 'contactgroups';
    \$rcmail_config['db_table_contactgroupmembers'] = 'contactgroupmembers';
    \$rcmail_config['db_table_session'] = 'session';
    \$rcmail_config['db_table_cache'] = 'cache';
    \$rcmail_config['db_table_messages'] = 'messages';
    \$rcmail_config['db_sequence_users'] = 'user_ids';
    \$rcmail_config['db_sequence_identities'] = 'identity_ids';
    \$rcmail_config['db_sequence_contacts'] = 'contact_ids';
    \$rcmail_config['db_sequence_contactgroups'] = 'contactgroups_ids';
    \$rcmail_config['db_sequence_cache'] = 'cache_ids';
    \$rcmail_config['db_sequence_messages'] = 'message_ids';


?>

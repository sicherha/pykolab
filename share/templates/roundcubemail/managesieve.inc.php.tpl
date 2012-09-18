<?php
    \$rcmail_config['managesieve_port'] = 4190;
    \$rcmail_config['managesieve_host'] = '%h';
    \$rcmail_config['managesieve_auth_type'] = 'PLAIN';
    \$rcmail_config['managesieve_auth_cid'] = null;
    \$rcmail_config['managesieve_auth_pw'] = null;
    \$rcmail_config['managesieve_usetls'] = true;
    \$rcmail_config['managesieve_default'] = '/etc/dovecot/sieve/global';
    \$rcmail_config['managesieve_mbox_encoding'] = 'UTF-8';
    \$rcmail_config['managesieve_replace_delimiter'] = '';
    \$rcmail_config['managesieve_disabled_extensions'] = array();
    \$rcmail_config['managesieve_debug'] = true;

    if (file_exists(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>

<?php
    \$config['managesieve_port'] = 4190;
    \$config['managesieve_host'] = '%h';
    \$config['managesieve_auth_type'] = 'PLAIN';
    \$config['managesieve_auth_cid'] = null;
    \$config['managesieve_auth_pw'] = null;
    \$config['managesieve_usetls'] = true;
    \$config['managesieve_default'] = '/etc/dovecot/sieve/global';
    \$config['managesieve_mbox_encoding'] = 'UTF-8';
    \$config['managesieve_replace_delimiter'] = '';
    \$config['managesieve_disabled_extensions'] = array();
    \$config['managesieve_debug'] = false;
    \$config['managesieve_vacation'] = 1;

    \$config['managesieve_filename_extension'] = '';
    \$config['managesieve_kolab_master'] = true;

    // ManageSieve Connection TLS settings, adjust for Production
    \$config['managesieve_conn_options'] = Array(
            'ssl' => Array(
                    'verify_peer_name' => false,
                    'verify_peer' => false,
                    'allow_self_signed' => true
                )
        );

    if (file_exists(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>

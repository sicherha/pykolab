<?php

    \$rcmail_config['kolab_freebusy_server'] = 'http://' . \$_SERVER["HTTP_HOST"] . '/freebusy';

    if (file_exists(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

    \$rcmail_config['kolab_cache'] = true;

    \$rcmail_config['kolab_ssl_verify_peer'] = false;

    \$rcmail_config['kolab_use_subscriptions'] = true;

?>

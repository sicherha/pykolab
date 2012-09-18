<?php
    // ownCloud URL
    \$rcmail_config['owncloud_url'] = 'http://' . \$_SERVER["HTTP_HOST"] . '/owncloud';

    if (file_exists(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>

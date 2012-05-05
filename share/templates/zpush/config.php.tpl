<?php
    /***********************************************
    * File      :   config.php
    * Project   :   Z-Push
    * Descr     :   Main configuration file
    *
    */

    define('KOLAB_SERVER', "$ldap_ldap_uri");
    define('KOLAB_LDAP_BASE',"$ldap_base_dn");
    define('KOLAB_BIND_DN',"$ldap_service_bind_dn");
    define('KOLAB_BIND_PW',"$ldap_service_bind_pw");
    define("KOLAB_LDAP_ACL","");
    define('KOLAB_IMAP_SERVER', "$imap_server");

    // Defines the default time zone
    if (function_exists("date_default_timezone_set")){
        date_default_timezone_set(date_default_timezone_get());
    }

    // Defines the base path on the server, terminated by a slash
    define('BASE_PATH', dirname($_SERVER['SCRIPT_FILENAME']) . "/");

    // Define the include paths
    ini_set(
            'include_path',
            BASE_PATH . "include/" . PATH_SEPARATOR .
            BASE_PATH . PATH_SEPARATOR .
            ini_get('include_path') . PATH_SEPARATOR .
            "/usr/share/php/" . PATH_SEPARATOR .
            "/usr/share/php5/" . PATH_SEPARATOR .
            "/usr/share/pear/"
    );

    define('STATE_DIR', 'state');

    // Try to set unlimited timeout
    define('SCRIPT_TIMEOUT', 0);

    //Max size of attachments to display inline. Default is 1MB
    define('MAX_EMBEDDED_SIZE', 1048576);

    // Device Provisioning
    define('PROVISIONING', true);

    // This option allows the 'loose enforcement' of the provisioning policies for older
    // devices which don't support provisioning (like WM 5 and HTC Android Mail) - dw2412 contribution
    // false (default) - Enforce provisioning for all devices
    // true - allow older devices, but enforce policies on devices which support it
    define('LOOSE_PROVISIONING', false);
    // Default conflict preference
    // Some devices allow to set if the server or PIM (mobile)
    // should win in case of a synchronization conflict
    //   SYNC_CONFLICT_OVERWRITE_SERVER - Server is overwritten, PIM wins
    //   SYNC_CONFLICT_OVERWRITE_PIM    - PIM is overwritten, Server wins (default)
    define('SYNC_CONFLICT_DEFAULT', SYNC_CONFLICT_OVERWRITE_PIM);

    // The data providers that we are using (see configuration below
    $BACKEND_PROVIDER = "BackendKolab";

    define("KOLAB_LDAP_ACL","");
    define('KOLAB_IMAP_NAMESPACES', Array(
                'personal' => "",
                'shared' => "Shared Folders",
                'users' => "Other Users"
            )
        );

    define('KOLAB_IMAP_PORT', 143);
    define('KOLAB_IMAP_OPTIONS', "/tls/novalidate-cert");

    define('KOLAB_INDEX',"/var/cache/kolab/z-push/kolabindex");

    //KolabMode
    //  0 = FlatMode
    //  1 = FolderMode
    //  2 = try to determine the mode
    define("KOLAB_MODE",2);
    // define which mobile support foldermode
    // this list is checked if KOLAB_MODE is set to 2
    define("KOLAB_MOBILES_FOLDERMODE","iphone:ipod:ipad");
    // folders by default if annotation is not found
    // possiblename1:possiblename2: ......
    // if no folders found the last found will be the default
    define('KOLAB_DEFAULTFOLDER_DIARY',"calendar:kalender:calendrier:agenda");
    define('KOLAB_DEFAULTFOLDER_CONTACT',"contacts:kontact");
    define('KOLAB_DEFAULTFOLDER_TASK',"task:taske");
    // If 1: shared folders will be read-only, even if the user have rights on it
    define('KOLAB_SHAREDFOLDERS_RO',"1");

    // Logfile
    define('KOLAB_LOGFILE',"/var/log/z-push/access.log");
     //For Gal
    define('SYNC_GAL_DISPLAYNAME','cn');
    define('SYNC_GAL_PHONE','telephonenumber');
    define('SYNC_GAL_OFFICE', '');
    define('SYNC_GAL_TITLE','title');
    define('SYNC_GAL_COMPANY','o');
    define('SYNC_GAL_ALIAS','uid');
    define('SYNC_GAL_FIRSTNAME','givenname');
    define('SYNC_GAL_LASTNAME','sn');
    define('SYNC_GAL_HOMEPHONE','homephone');
    define('SYNC_GAL_MOBILEPHONE','mobile');
    define('SYNC_GAL_EMAILADDRESS','mail');

?>

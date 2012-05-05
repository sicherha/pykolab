<?php
/**
 * This file provides configuration settings for both the freebusy.php
 * and the pfb.php scripts.
 *
 * \$Horde: framework/Kolab_FreeBusy/www/Horde/Kolab/FreeBusy/config.php,v 1.4.2.2 2010/07/22 13:55:30 wrobel Exp \$
 *
 * Copyright 2008-2009 The Horde Project (http://www.horde.org/)
 *
 * @author  Steffen Hansen <steffen@klaralvdalens-datakonsult.se>
 * @author  Gunnar Wrobel <p@rdus.de>
 * @author  Thomas Arendsen Hein <thomas@intevation.de>
 * @package Kolab_FreeBusy
 */

\$conf = array();

/* Horde::Log configuration */
\$conf['log']['enabled']          = true;
\$conf['log']['priority']         = PEAR_LOG_DEBUG;
\$conf['log']['type']             = 'file';
\$conf['log']['name']             = '/var/log/kolab/freebusy/freebusy.log';
\$conf['log']['ident']            = 'Kolab Free/Busy';
\$conf['log']['params']['append'] = true;

/* PHP error logging */
ini_set('error_log', '/var/log/kolab/freebusy/php.log');

/* Horde::Kolab::LDAP configuration */
\$conf['kolab']['ldap']['server'] = 'localhost';
\$conf['kolab']['ldap']['basedn'] = '$ldap_base_dn';
\$conf['kolab']['ldap']['phpdn']  = '$ldap_service_bind_dn';
\$conf['kolab']['ldap']['phppw']  = '$ldap_service_bind_pw';

/* Horde::Kolab::IMAP configuration */
\$conf['kolab']['imap']['server']   = 'localhost';
\$conf['kolab']['imap']['port']     = 143;
\$conf['kolab']['imap']['protocol'] = 'imap/tls/novalidate-cert/readonly';
\$conf['kolab']['imap']['namespaces'] = array(
    array('type' => 'personal', 'name' => '', 'delimiter' => '/'),
    array('type' => 'other', 'name' => 'Other Users', 'delimiter' => '/'),
    array('type' => 'shared', 'name' => 'Shared Folders', 'delimiter' => '/'),
);

/* Horde::Auth configuration */
\$conf['auth']['params']['login_block'] = 0;
\$conf['auth']['checkbrowser']          = false;
\$conf['auth']['checkip']               = false;
\$conf['umask'] = false;

\$conf['auth']['driver'] = 'imap';
\$conf['auth']['params']['hostspec'] = 'localhost';
\$conf['auth']['params']['protocol'] = 'imap/tls/novalidate-cert';

/* Allow special users to log into the system */
\$conf['kolab']['imap']['allow_special_users'] = true;

/* Do not record login attempts */
\$conf['auth']['params']['login_block'] = false;

/* Kolab::Freebusy configuration */

/* Should we redirect using a Location header, if the user is not local? If this
 * is false we silently download the file ourselves and output it so that it
 * looks as though the free/busy information is coming from us.
 */
\$conf['fb']['redirect']     = false;

/* What is the address of the current server where the calendar data is stored?
 * This is also used as the LDAP server address where user objects reside.
 */
\$conf['kolab']['freebusy']['server']  = 'http://' . \$_SERVER["HTTP_HOST"] . '/freebusy';

/* What is our default mail domain? This is used if any users do not have
 * '@domain' specified after their username as part of their email address.
 */
\$conf['fb']['email_domain'] = '$primary_domain';

/* Location of the cache files */
\$conf['fb']['cache_dir']    = '/tmp';
\$conf['fb']['cache']['driver'] = 'sql';
\$conf['fb']['cache']['params']['phptype'] = 'mysql';
\$conf['fb']['cache']['params']['username'] = 'roundcube';
\$conf['fb']['cache']['params']['password'] = '$mysql_roundcube_password';
\$conf['fb']['cache']['params']['hostspec'] = 'localhost';
\$conf['fb']['cache']['params']['database'] = 'roundcube';
\$conf['fb']['cache']['params']['charset'] = 'utf-8';

/* What db type to use for the freebusy caches */
\$conf['fb']['dbformat']     = 'db4';

/* Should we send a Content-Type header, indicating what the mime type of the
 * resulting VFB file is?
 */
\$conf['fb']['send_content_type'] = false;

/* Should we send a Content-Length header, indicating how large the resulting
 * VFB file is?
 */
\$conf['fb']['send_content_length'] = false;

/* Should we send a Content-Disposition header, indicating what the name of the
 * resulting VFB file should be?
 */
\$conf['fb']['send_content_disposition'] = false;

/* Should we use ACLs or does everybody get full rights? DO NOT set
 * this to false if you don't know what you are doing. Your free/busy
 * service should not be visible to any outside networks when
 * disabling the use of ACL settings.
 */
\$conf['fb']['use_acls'] = true;

/* How many days in advance should the free/busy information be calculated? This
 * is the default value that can be overwritten by the kolabFreeBusyFuture
 * attribute of the users LDAP account.
 */
\$conf['fb']['future_days'] = 180;

/* The resulting vCalendar file is being cached. The following setting
 * determines how many seconds it will be delivered without checking if
 * the contents of the file might have changed. A negative setting disables
 * caching (which is currently required for the resource management to work).
 */
\$conf['fb']['vcal_cache']['min_age'] = -1;

/* The resulting vCalendar file is being cached. The following setting
 * determines after how many seconds it will be considered too old for
 * delivery and a refresh of its contents will be enforced.
 */
\$conf['fb']['vcal_cache']['max_age'] = 259200;

/* The IMAP namespaces on the server. @TODO: Should obviously be
 * auto-detected.
 */
\$conf['fb']['namespace']['personal'] = '';
\$conf['fb']['namespace']['other'] = 'Other Users';

/* In most cases you can rely on the standard event status to free/busy status
 * mapping. For the default kolab server this will mean that only the event
 * status "free" will be mapped to the free/busy status "FREE". All other event
 * status ("tentative", "busy", "outofoffice") will be mapped to "BUSY".
 *
 * If this mapping should be modified you can define it like this:
 *
 * \$conf['fb']['status_map'] = array(
 *    Horde_Kolab_FreeBusy_Object_Event::STATUS_TENTATIVE =>
 *    Horde_Kolab_FreeBusy_Helper_Freebusy_StatusMap::STATUS_BUSY_TENTATIVE,
 *    Horde_Kolab_FreeBusy_Object_Event::STATUS_OUTOFOFFICE =>
 *    'X-OUT-OF-OFFICE',
 * );
 */
require_once 'Horde/Kolab/FreeBusy/Object/Event.php';
require_once 'Horde/Kolab/FreeBusy/Helper/Freebusy/StatusMap.php';
\$conf['fb']['status_map'] = array(
    Horde_Kolab_FreeBusy_Object_Event::STATUS_TENTATIVE =>
    Horde_Kolab_FreeBusy_Helper_Freebusy_StatusMap::STATUS_BUSY_TENTATIVE,
    Horde_Kolab_FreeBusy_Object_Event::STATUS_OUTOFOFFICE =>
    'X-OUT-OF-OFFICE',
);

/* Are there remote servers on which users have additional (shared)
 * folders? In that case free/busy information should also be fetched
 * from these servers.
 *
 * Add them like this:
 *
 * array('remote1.example.com', 'remote2.example.com')
 */
\$conf['fb']['remote_servers'] = array();

/* Is there an exchange server that you want to relay through this free/busy
 * application?
 *
 * Configure it like this:
 *
 * \$conf['fb']['exchange_server'] = array(
 *    'url' => 'https://example.com',
 *    'interval' => 30,
 * );
 */
#\$conf['fb']['exchange_server'] = array(
#    'url' => 'http://test90-9.test90.kolabsys.com',
#    'interval' => 30,
#    'username' => 'kolabservice',
#    'password' => 'SomePass',
#);

/**
 * Ensure we use the Kolab group driver when handling groups.
 */
\$conf['group']['driver'] = 'kolab';
\$conf['group']['cache'] = false;

//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
//
// If you modify this file, please do not forget to also modify the
// template in kolabd!
//
//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

// DEBUGGING
// =========
//
// Activate this to see the log messages on the screen
// \$conf['log']['type'] = 'display';
//
// Activate this to see the php messages on the screen
// ini_set('display_errors', 1);
//
// Both settings will disrupt header delivery (which should not cause a
// problem).

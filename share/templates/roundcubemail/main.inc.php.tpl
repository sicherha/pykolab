<?php
    \$rcmail_config = array();

    \$rcmail_config['imap_cache'] = 'db';
    \$rcmail_config['messages_cache'] = 'db';
    \$rcmail_config['force_https'] = false;
    \$rcmail_config['use_https'] = false;
    \$rcmail_config['login_autocomplete'] = 0;
    \$rcmail_config['session_lifetime'] = 180;
    \$rcmail_config['ip_check'] = false;
    \$rcmail_config['referer_check'] = false;
    \$rcmail_config['password_charset'] = 'ISO-8859-1';
    \$rcmail_config['sendmail_delay'] = 0;
    \$rcmail_config['max_recipients'] = 0;
    \$rcmail_config['max_group_members'] = 0;
    \$rcmail_config['useragent'] = 'Roundcube Webmail/'.RCMAIL_VERSION;
    \$rcmail_config['include_host_config'] = false;
    \$rcmail_config['generic_message_footer'] = '';
    \$rcmail_config['generic_message_footer_html'] = '';
    \$rcmail_config['http_received_header'] = true;
    \$rcmail_config['http_received_header_encrypt'] = true;
    \$rcmail_config['mail_header_delimiter'] = NULL;
    \$rcmail_config['line_length'] = 72;
    \$rcmail_config['send_format_flowed'] = true;
    \$rcmail_config['dont_override'] = Array();
    \$rcmail_config['identities_level'] = 0;
    \$rcmail_config['contact_photo_size'] = 160;
    \$rcmail_config['email_dns_check'] = false;

    \$rcmail_config['message_sort_col'] = '';
    \$rcmail_config['message_sort_order'] = 'DESC';
    \$rcmail_config['list_cols'] = array('subject', 'status', 'from', 'date', 'size', 'flag', 'attachment');
    \$rcmail_config['language'] = null;
    \$rcmail_config['date_short'] = 'D H:i';
    \$rcmail_config['date_long'] = 'd.m.Y H:i';
    \$rcmail_config['date_today'] = 'H:i';
    \$rcmail_config['date_format'] = 'Y-m-d';
    \$rcmail_config['quota_zero_as_unlimited'] = false;
    \$rcmail_config['enable_spellcheck'] = true;
    \$rcmail_config['spellcheck_dictionary'] = true;
    \$rcmail_config['spellcheck_engine'] = 'googie';
    \$rcmail_config['spellcheck_uri'] = '';
    \$rcmail_config['spellcheck_languages'] = NULL;
    \$rcmail_config['spellcheck_ignore_caps'] = true;
    \$rcmail_config['spellcheck_ignore_nums'] = true;
    \$rcmail_config['spellcheck_ignore_syms'] = true;
    \$rcmail_config['max_pagesize'] = 200;
    \$rcmail_config['min_keep_alive'] = 60;
    \$rcmail_config['undo_timeout'] = 10;
    \$rcmail_config['upload_progress'] = 2;
    \$rcmail_config['address_book_type'] = 'ldap';
    \$rcmail_config['autocomplete_min_length'] = 3;
    \$rcmail_config['autocomplete_threads'] = 0;
    \$rcmail_config['autocomplete_max'] = 15;
    \$rcmail_config['address_template'] = '{street}<br/>{locality} {zipcode}<br/>{country} {region}';
    \$rcmail_config['default_charset'] = 'ISO-8859-1';
    \$rcmail_config['pagesize'] = 40;
    \$rcmail_config['timezone'] = 'auto';
    \$rcmail_config['dst_active'] = (bool)date('I');
    \$rcmail_config['prefer_html'] = true;
    \$rcmail_config['show_images'] = 0;
    \$rcmail_config['prettydate'] = true;
    \$rcmail_config['draft_autosave'] = 300;
    \$rcmail_config['preview_pane'] = true;
    \$rcmail_config['preview_pane_mark_read'] = 0;
    \$rcmail_config['logout_purge'] = false;
    \$rcmail_config['logout_expunge'] = false;
    \$rcmail_config['inline_images'] = true;
    \$rcmail_config['mime_param_folding'] = 1;
    \$rcmail_config['skip_deleted'] = true;
    \$rcmail_config['read_when_deleted'] = true;
    \$rcmail_config['flag_for_deletion'] = true;
    \$rcmail_config['keep_alive'] = 300;
    \$rcmail_config['check_all_folders'] = false;
    \$rcmail_config['display_next'] = true;
    \$rcmail_config['autoexpand_threads'] = 2;
    \$rcmail_config['top_posting'] = false;
    \$rcmail_config['strip_existing_sig'] = true;
    \$rcmail_config['show_sig'] = 1;
    \$rcmail_config['sig_above'] = false;
    \$rcmail_config['force_7bit'] = false;
    \$rcmail_config['search_mods'] = null;
    \$rcmail_config['delete_always'] = true;
    \$rcmail_config['mdn_requests'] = 0;
    \$rcmail_config['mdn_default'] = false;
    \$rcmail_config['dsn_default'] = false;
    \$rcmail_config['reply_same_folder'] = false;

    \$rcmail_config['plugins'] = array(
            'acl',
            'archive',
            'calendar',
            'compose_addressbook',
            'http_authentication',
            'jqueryui',
            'kolab_activesync',
            'kolab_addressbook',
            'kolab_auth',
            'kolab_core',
            'kolab_config',
            'kolab_folders',
            'listcommands',
            'managesieve',
            'newmail_notifier',
            'odfviewer',
            'password',
            'redundant_attachments',
            'tasklist',
            'threading_as_default',
            // contextmenu must be after kolab_addressbook (#444)
            'contextmenu',
        );


    if (file_exists(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/main.inc.php')) {
        include_once(RCMAIL_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/main.inc.php');
    }

    // Re-apply mandatory settings here.

    \$rcmail_config['debug_level'] = 0;
    \$rcmail_config['devel_mode'] = false;
    \$rcmail_config['log_driver'] = 'file';
    \$rcmail_config['log_date_format'] = 'd-M-Y H:i:s,u O';
    \$rcmail_config['syslog_id'] = 'roundcube';
    \$rcmail_config['syslog_facility'] = LOG_USER;
    \$rcmail_config['smtp_log'] = true;
    \$rcmail_config['log_logins'] = true;
    \$rcmail_config['log_session'] = true;
    \$rcmail_config['sql_debug'] = true;
    \$rcmail_config['memcache_debug'] = true;
    \$rcmail_config['imap_debug'] = true;
    \$rcmail_config['ldap_debug'] = true;
    \$rcmail_config['smtp_debug'] = true;

    \$rcmail_config['product_name'] = 'Kolab Groupware';

    \$rcmail_config['skin'] = 'default';
    \$rcmail_config['skin_logo'] = 'skins/kolab/images/kolab_logo.png';
    \$rcmail_config['skin_include_php'] = false;
    \$rcmail_config['mime_magic'] = '/usr/share/misc/magic';
    \$rcmail_config['im_identify_path'] = '/usr/bin/identify';
    \$rcmail_config['im_convert_path'] = '/usr/bin/convert';
    \$rcmail_config['login_lc'] = true;
    \$rcmail_config['auto_create_user'] = true;
    \$rcmail_config['enable_installer'] = false;
    \$rcmail_config['session_storage'] = 'db';
    \$rcmail_config['default_port'] = 143;
    \$rcmail_config['imap_auth_type'] = '';
    \$rcmail_config['imap_delimiter'] = '/';
    \$rcmail_config['imap_ns_personal'] = null;
    \$rcmail_config['imap_ns_other']    = null;
    \$rcmail_config['imap_ns_shared']   = null;
    \$rcmail_config['imap_force_caps'] = false;
    \$rcmail_config['imap_force_lsub'] = true;
    \$rcmail_config['imap_timeout'] = 0;
    \$rcmail_config['imap_auth_cid'] = null;
    \$rcmail_config['imap_auth_pw'] = null;
    \$rcmail_config['smtp_port'] = 587;
    \$rcmail_config['smtp_user'] = '%u';
    \$rcmail_config['smtp_pass'] = '%p';
    \$rcmail_config['smtp_auth_type'] = '';
    \$rcmail_config['smtp_auth_cid'] = null;
    \$rcmail_config['smtp_auth_pw'] = null;
    \$rcmail_config['smtp_helo_host'] = \$_SERVER["HTTP_HOST"];
    \$rcmail_config['smtp_timeout'] = 0;
    \$rcmail_config['log_dir'] = '/var/log/roundcubemail/';
    \$rcmail_config['temp_dir'] = '\${_tmppath}';
    \$rcmail_config['message_cache_lifetime'] = '10d';

    \$rcmail_config['archive_mbox'] = 'Archive';
    \$rcmail_config['drafts_mbox'] = 'Drafts';
    \$rcmail_config['junk_mbox'] = 'Spam';
    \$rcmail_config['sent_mbox'] = 'Sent';
    \$rcmail_config['trash_mbox'] = 'Trash';
    \$rcmail_config['default_imap_folders'] = array('INBOX', 'Drafts', 'Sent', 'Spam', 'Trash');
    \$rcmail_config['create_default_folders'] = true;
    \$rcmail_config['protect_default_folders'] = true;

    \$mandatory_plugins = Array(
            'calendar',
            'kolab_addressbook',
            'kolab_auth',
            'kolab_core',
            'kolab_config',
            'kolab_folders',
            'password',
        );

    foreach ( \$mandatory_plugins as \$num => \$plugin ) {
        if (!in_array(\$plugin, \$rcmail_config['plugins'])) {
                \$rcmail_config['plugins'][] = \$plugin;
        }
    }

    \$rcmail_config['default_host'] = 'tls://localhost';
    \$rcmail_config['smtp_server'] = 'tls://localhost';
    \$rcmail_config['session_domain'] = '';
    \$rcmail_config['des_key'] = "$des_key";
    \$rcmail_config['username_domain'] = '';

    \$rcmail_config['mail_domain'] = '';

    \$rcmail_config['ldap_public'] = array(
            'kolab_addressbook' => array(
                    'name'                      => 'Global Address Book',
                    'hosts'                     => Array('localhost'),
                    'port'                      => 389,
                    'use_tls'                   => false,
                    'base_dn'                   => '$ldap_user_base_dn',
                    'user_specific'             => true,
                    'bind_dn'                   => '%dn',
                    'bind_pass'                 => '',
                    'search_base_dn'            => '$ldap_user_base_dn',
                    'search_bind_dn'            => '$ldap_service_bind_dn',
                    'search_bind_pw'            => '$ldap_service_bind_pw',
                    'search_filter'             => '(&(objectClass=inetOrgPerson)(mail=%fu))',
                    'writable'                  => false,
                    'LDAP_Object_Classes'       => array("top", "inetOrgPerson"),
                    'required_fields'           => array("cn", "sn", "mail"),
                    'LDAP_rdn'                  => 'uid',
                    'ldap_version'              => 3,       // using LDAPv3
                    'search_fields'             => array('displayname', 'mail'),
                    'sort'                      => array('displayname', 'sn', 'givenname', 'cn'),
                    'scope'                     => 'sub',
                    'filter'                    => '(objectClass=inetOrgPerson)',
                    'vlv'                       => false,
                    'vlv_search'                => false,
                    'fuzzy_search'              => true,
                    'sizelimit'                 => '0',
                    'timelimit'                 => '0',
                    'fieldmap'                  => Array(
                            // Roundcube        => LDAP
                            'name'              => 'displayName',
                            'surname'           => 'sn',
                            'firstname'         => 'givenName',
                            'middlename'        => 'initials',
                            'prefix'            => 'title',
                            'email:primary'     => 'mail',
                            'email:alias'       => 'alias',
                            'phone:main'        => 'telephoneNumber',
                            'phone:work'        => 'alternateTelephoneNumber',
                            'phone:mobile'      => 'mobile',
                            'phone:work2'       => 'blackberry',
                            'jobtitle'          => 'title',
                            'manager'           => 'manager',
                            'assistant'         => 'secretary',
                            'photo'             => 'jpegphoto'
                        ),
                    'groups'                    => Array(
                            'base_dn'           => '$ldap_group_base_dn',
                            'filter'            => '(&' . '$ldap_group_filter' . '(mail=*))',
                            'object_classes'    => Array("top", "groupOfUniqueNames"),
                            'member_attr'       => 'uniqueMember',
                        ),
                ),
        );

    \$rcmail_config['autocomplete_addressbooks'] = Array(
            'kolab_addressbook'
        );

    \$rcmail_config['autocomplete_single'] = true;

    \$rcmail_config['htmleditor'] = 0;

    include_once("/etc/roundcubemail/kolab_auth.inc.php");

    \$rcmail_config['kolab_cache'] = true;

?>

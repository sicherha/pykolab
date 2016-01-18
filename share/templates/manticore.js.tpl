'use strict';

// Use local.env.js for environment variables that grunt will set when the server starts locally.
// Use for your api keys, secrets, etc. This file should not be tracked by git.
//
// You will need to set these on the server you deploy to.

module.exports = {
  DOMAIN:           'http://$fqdn:8080',
  SESSION_SECRET:   'manticore-secret',

  // Control debug level for modules using visionmedia/debug
  DEBUG: '',

  DEFAULT_ACCESS: 'deny',

  AUTH: 'ldap',
  STORAGE: 'chwala',

  CHWALA_SERVER: 'http://$fqdn/chwala/api/document',
  ROUNDCUBE_SERVER: 'http://$fqdn/roundcubemail',

  AUTH_ENCRYPTION_KEY: 'suchauth123muchkey456',

  LDAP_SERVER: 'ldap://$server_host:389',
  LDAP_BASE: '$user_base_dn',
  LDAP_FILTER: '(&(objectclass=kolabinetorgperson)(|(uid={{username}})(mail={{username}})))',
  LDAP_BIND_DN: '$service_bind_dn',
  LDAP_BIND_PW: '$service_bind_pw'

};

<?php
    \$rcmail_config['calendar_driver'] = "kolab";
    \$rcmail_config['calendar_default_view'] = "agendaWeek";
    \$rcmail_config['calendar_timeslots'] = 2;
    \$rcmail_config['calendar_first_day'] = 1;
    \$rcmail_config['calendar_first_hour'] = 6;
    \$rcmail_config['calendar_work_start'] = 6;
    \$rcmail_config['calendar_work_end'] = 18;
    \$rcmail_config['calendar_event_coloring'] = 0;

    if (file_exists(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>

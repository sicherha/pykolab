<?php
    \$config['calendar_driver'] = "kolab";
    \$config['calendar_default_view'] = "agendaWeek";
    \$config['calendar_timeslots'] = 2;
    \$config['calendar_first_day'] = 1;
    \$config['calendar_first_hour'] = 6;
    \$config['calendar_work_start'] = 6;
    \$config['calendar_work_end'] = 18;
    \$config['calendar_event_coloring'] = 0;
    \$config['calendar_caldav_url'] = 'http://' . \$_SERVER['HTTP_HOST'] . '/iRony/calendars/%u/%i';

    if (file_exists(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__))) {
        include_once(RCUBE_CONFIG_DIR . '/' . \$_SERVER["HTTP_HOST"] . '/' . basename(__FILE__));
    }

?>

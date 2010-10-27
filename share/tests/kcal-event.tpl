From: %(from_name_str)s <%(from_email_str)s>
To: %(to_name_str)s <%(to_email_str)s>
Subject: libkcal-%(uid)s
Date: %(rfc_2822_sent_date)s
MIME-Version: 1.0
X-Kolab-Type: application/x-vnd.kolab.event
Content-Type: Multipart/Mixed;
  boundary="Boundary-00=%(uid)s"
Status: RO
X-Status: OT
X-KMail-EncryptionState:
X-KMail-SignatureState:
X-KMail-MDN-Sent:
X-UID: 0

--Boundary-00=%(uid)s
Content-Type: Text/Plain;
  charset="us-ascii"
Content-Transfer-Encoding: 7bit
Content-Disposition:

This is a Kolab Groupware object.
To view this object you will need an email client that can understand the Kolab Groupware format.
For a list of such email clients please visit
http://www.kolab.org/kolab2-clients.html
--Boundary-00=%(uid)s
Content-Type: application/x-vnd.kolab.event;
  name="kolab.xml"
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment;
  filename="kolab.xml"

<?xml version="1.0" encoding="UTF-8"?>
<event version="1.0">
 <product-id>KOrganizer 4.4.5, Kolab resource</product-id>
 <uid>libkcal-%(uid)s</uid>
 <creation-date>%(kolab_event_date_creation)s</creation-date>
 <last-modification-date>2010-10-21T13:42:14+00:00</last-modification-date>
 <sensitivity>public</sensitivity>
 <start-date>%(kolab_event_date_start)s</start-date>
 <summary>%(event_summary)s</summary>
 <location>%(event_location)s</location>
 <organizer>
  <display-name>%(from_name_str)s</display-name>
  <smtp-address>%(from_email_str)s</smtp-address>
 </organizer>
 <attendee>
  <display-name>%(to_name_str)s</display-name>
  <smtp-address>%(to_email_str)s</smtp-address>
  <status>accepted</status>
  <request-response>false</request-response>
  <invitation-sent>false</invitation-sent>
  <role>required</role>
 </attendee>%(event_recurrence)s
 <alarm>15</alarm>
 <advanced-alarms>
  <alarm type="display">
   <enabled>1</enabled>
   <start-offset>-15</start-offset>
  </alarm>
 </advanced-alarms>
 <revision>0</revision>
 <show-time-as>busy</show-time-as>
 <end-date>%(kolab_event_date_end)s</end-date>
</event>

--Boundary-00=%(uid)s--

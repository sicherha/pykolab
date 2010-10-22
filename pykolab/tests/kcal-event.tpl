From: @@user@@ von Test <@@user_email@@>
Subject: libkcal-@@uid@@
Date: Thu, 21 Oct 2010 14:40:32 +0100
MIME-Version: 1.0
X-Kolab-Type: application/x-vnd.kolab.event
Content-Type: Multipart/Mixed;
  boundary="Boundary-00=@@uid@@"
Status: RO
X-Status: OT
X-KMail-EncryptionState:
X-KMail-SignatureState:
X-KMail-MDN-Sent:
X-UID: 0

--Boundary-00=@@uid@@
Content-Type: Text/Plain;
  charset="us-ascii"
Content-Transfer-Encoding: 7bit
Content-Disposition:

This is a Kolab Groupware object.
To view this object you will need an email client that can understand the Kolab Groupware format.
For a list of such email clients please visit
http://www.kolab.org/kolab2-clients.html
--Boundary-00=@@uid@@
Content-Type: application/x-vnd.kolab.event;
  name="kolab.xml"
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment;
  filename="kolab.xml"

<?xml version="1.0" encoding="UTF-8"?>
<event version="1.0">
 <product-id>KOrganizer 4.4.5, Kolab resource</product-id>
 <uid>libkcal-@@uid@@</uid>
 <creation-date>2010-10-21T13:40:32Z</creation-date>
 <last-modification-date>2010-10-21T13:42:14+00:00</last-modification-date>
 <sensitivity>public</sensitivity>
 <start-date>@@date_start@@T@@time_start@@:00:00Z</start-date>
 <summary>test event</summary>
 <location>somewhere else</location>
 <organizer>
  <display-name>@@user@@ von Test</display-name>
  <smtp-address>@@user_email@@</smtp-address>
 </organizer>
 <attendee>
  <display-name>@@user@@ von Test</display-name>
  <smtp-address>@@user_email@@</smtp-address>
  <status>accepted</status>
  <request-response>false</request-response>
  <invitation-sent>false</invitation-sent>
  <role>required</role>
 </attendee>@@recurrence@@
 <alarm>15</alarm>
 <advanced-alarms>
  <alarm type="display">
   <enabled>1</enabled>
   <start-offset>-15</start-offset>
  </alarm>
 </advanced-alarms>
 <revision>0</revision>
 <show-time-as>busy</show-time-as>
 <end-date>@@date_end@@T@@time_end@@:00:00Z</end-date>
</event>

--Boundary-00=@@uid@@--

From: %(from_name_str)s <%(from_email_str)s>
To: %(to_name_str)s <%(to_email_str)s>
Subject: %(uid)s
Date: %(rfc_2822_sent_date)s
MIME-Version: 1.0
X-Kolab-Type: application/x-vnd.kolab.contact
Content-Type: Multipart/Mixed;
  boundary="Boundary-00=%(uid)s"

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
Content-Type: application/x-vnd.kolab.contact;
  name="kolab.xml"
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment;
  filename="kolab.xml"

<?xml version="1.0" encoding="UTF-8"?>
<contact version="1.0">
 <product-id>KAddressBook 3.3, Kolab resource</product-id>
 <uid>%(uid)s</uid>
 <body>body</body>
 <creation-date>%(kolab_creation_date)s</creation-date>
 <sensitivity>public</sensitivity>
 <name>
  <given-name>%(kolab_contact_given_name)s</given-name>
  <last-name>%(kolab_contact_last_name)s</last-name>
  <full-name>%(kolab_contact_given_name)s %(kolab_contact_last_name)s</full-name>
 </name>
 <organization></organization>
 <web-page></web-page>
 <role></role>
 <email>
   <display-name>%(kolab_contact_given_name)s %(kolab_contact_last_name)s</display-name>
   <smtp-address>%(kolab_contact_email_str)s</smtp-address>
 </email>
 <phone>
    <type>mobile</type>
    <number>%(kolab_contact_mobile_number)s</number>
 </phone>
 <preferred-address></preferred-address>
</contact>

--Boundary-00=%(uid)s--

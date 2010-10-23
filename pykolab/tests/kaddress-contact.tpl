From: @@user@@ <@@user_email@@>
Subject: @@uid@@
Date: Thu, 20 May 2010 09:04:51 +0100
MIME-Version: 1.0
X-Kolab-Type: application/x-vnd.kolab.contact
Content-Type: Multipart/Mixed;
  boundary="Boundary-00=@@uid@@"
Status: RO
X-Status: OT
X-KMail-EncryptionState:
X-KMail-SignatureState:
X-KMail-MDN-Sent:
X-UID: 57

--Boundary-00=@@uid@@
Content-Type: Text/Plain;
  charset="us-ascii"
Content-Transfer-Encoding: 7bit

This is a Kolab Groupware object.
To view this object you will need an email client that can understand the Kolab Groupware format.
For a list of such email clients please visit
http://www.kolab.org/kolab2-clients.html
--Boundary-00=@@uid@@
Content-Type: application/x-vnd.kolab.contact;
  name="kolab.xml"
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment;
  filename="kolab.xml"

<?xml version="1.0" encoding="UTF-8"?>
<contact version="1.0">
 <product-id>KAddressBook 3.3, Kolab resource</product-id>
 <uid>@@uid@@</uid>
 <sensitivity>public</sensitivity>
 <name>
  <given-name>@@given_name@@</given_name>
  <middle-names>@@middle_names@@</middle-names>
  <last-name>@@last_name@@</last-name>
  <full-name>@@full_name@@</full-name>
 </name>
 <email>
   <display-name>@@display_name@@</display-name>
   <smtp-address>@@email_address@@</smtp-address>
 </email>
 <phone>
    <type>mobile</type>
    <number>@@number@@</number>
 </phone>
 <birthday>@@birthday@@</birthday>
 <preferred-address>home</preferred-address>
</contact>

--Boundary-00=@@uid@@--

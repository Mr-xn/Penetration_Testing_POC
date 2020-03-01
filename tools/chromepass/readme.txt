
Zip File Password: chpass9126*

ChromePass v1.50
Copyright (c) 2008 - 2020 Nir Sofer
Web site: https://www.nirsoft.net



Description
===========

ChromePass is a small password recovery tool that allows you to view the
user names and passwords stored by Google Chrome Web browser. For each
password entry, the following information is displayed: Origin URL,
Action URL, User Name Field, Password Field, User Name, Password, and
Created Time. It allows you to get the passwords from your current
running system, or from a user profile stored on external drive.
You can select one or more items and then save them into text/html/xml
file or copy them to the clipboard.



Versions History
================


* Version 1.50:
  o Added support for the new password encryption of Chromium /
    Chrome Web browsers, starting from version 80.
  o Be aware that the 'Local State' file, located inside the 'User
    Data' folder (Parent of your Chrome profile folder), is needed for
    decrypting the passwords of Chrome 80 or later.
  o In most cases, ChromePass will find your 'Local State' file
    automatically, but if it fails to find this file from some reason,
    you can manually type the 'Local State' filename in the 'Advanced
    Options' window.

* Version 1.47:
  o Added new file format to export the passwords: Chrome CSV File.
    It's the same file format that Chrome Web browser exports the
    passwords from chrome://settings/passwords

* Version 1.46:
  o Fixed bug: When using the 'Advanced external drive settings' in
    the 'Advanced Options' window, ChromePass displayed an error message.
  o ChromePass now saves the Advanced external drive settings in the
    .cfg file.

* Version 1.45:
  o Added 'Run As Administrator' option (Ctrl+F11), which allows you
    to easily run ChromePass as administrator on Windows
    Vista/7/8/2008/10. You may need to run ChromePass as administrator
    when reading passwords from external drive.
  o ChromePass now displays an error message if it cannot access the
    files on external drive.

* Version 1.42:
  o ChromePass now automatically displays the passwords of Vivaldi
    Web browser.

* Version 1.41:
  o Added support for exporting to XML file of Password Exporter
    Firefox extension, so you can import the passwords of Chrome into
    Firefox using the this Firefox extension.

* Version 1.40:
  o Passwords decryption of external drive / profile now works on all
    versions of Windows, starting from Windows XP and up to Windows 10 !
    ('Advanced Options' window - F9)
  o Added advanced external drive settings which allows you to choose
    the desired Windows Protect folder and the 'User Data' folder of
    Chrome ('Advanced Options' window - F9).

* Version 1.37:
  o Added 'Mark Odd/Even Rows' option.

* Version 1.36:
  o Fixed bug: ChromePass failed to export to KeePass csv file.

* Version 1.35:
  o ChromePass now also displays the passwords of Opera and Yandex
    Web browsers (Both of them are based on Chrome...)
  o Added 'Password File' column.

* Version 1.32:
  o Fixed ChromePass to display the correct 'Created Time' on the
    latest versions of Chrome.

* Version 1.31:
  o Fixed ChromePass to display properly user name/password with
    non-English characters.

* Version 1.30:
  o Added option to specify a profile folder ('Use the following
    profile folder:' check-box)

* Version 1.27:
  o Added support for Chromium.

* Version 1.26:
  o Removed the command-line options that export the passwords to a
    file from the official version. A version of this tool with full
    command-line support will be posted on separated Web page.

* Version 1.25:
  o ChromePass now automatically reads the passwords from all
    profiles of Chrome Web browser.
  o Fixed issue: The properties dialog-box and other windows opened
    in the wrong monitor, on multi-monitors system.

* Version 1.22:
  o Fixed bug: ChromePass failed to read the password file if the
    file path contained non-English characters.

* Version 1.21:
  o Added support for Chrome Canary.

* Version 1.20:
  o Fixed ChromePass to work properly when the password file is
    locked by Chrome.

* Version 1.16:
  o Added an option to export the passwords into KeePass csv file (In
    'Save Selected Items'). You can use the created csv file to easily
    import your Web site passwords into KeePass password manager.
  o Fixed issue: removed the wrong encoding from the xml string,
    which caused problems to some xml viewers.

* Version 1.15: Added 'Password Strength' column, which calculates the
  strength of the password and displays it as Very Weak, Weak, Medium,
  Strong, or Very Strong.
* Version 1.10: Fixed ChromePass to work with the latest versions of
  Chrome.
* Version 1.05: Added support for recovering Chrome passwords from
  external drive. (In Advanced Options)
* Version 1.00: First release.



Using ChromePass
================

ChromePass doesn't require any installation process or additional DLL
files. In order to start using ChromePass, simply run the executable file
- ChromePass.exe After running it, the main window will display all
passwords that are currently stored in your Google Chrome browser.



Reading ChromePass passwords from external drive
================================================

Starting from version 1.05, you can also read the passwords stored by
Chrome Web browser from an external profile in your current operating
system or from another external drive (For example: from a dead system
that cannot boot anymore). In order to use this feature, you must know
the last logged-on password used for this profile, because the passwords
are encrypted with the SHA hash of the log-on password, and without that
hash, the passwords cannot be decrypted.
You can use this feature from the UI, by selecting the 'Advanced Options'
in the File menu, or from command-line, by using /external parameter. The
user profile path should be something like "C:\Documents and
Settings\admin" in Windows XP/2003 or "C:\users\myuser" in Windows
10/8/7/Vista/2008.




Command-Line Options
====================



/stext <Filename>
Save the list of passwords into a regular text file.

/stab <Filename>
Save the list of passwords into a tab-delimited text file.

/scomma <Filename>
Save the list of passwords into a comma-delimited text file.

/stabular <Filename>
Save the list of passwords into a tabular text file.

/shtml <Filename>
Save the list of passwords into HTML file (Horizontal).

/sverhtml <Filename>
Save the list of passwords into HTML file (Vertical).

/sxml <Filename>
Save the list of passwords to XML file.

/skeepass <Filename>
Save the list of passwords to KeePass csv file.

/spassexp <Filename>
Save the list of passwords to XML file of Password Exporter Firefox
extension.

/external <User Profile Path> <Last Log-On Password>
Load the Chrome passwords from external drive/profile. For example:
chromepass.exe /external "C:\Documents and Settings\admin" "MyPassword"



Translating ChromePass to other languages
=========================================

In order to translate ChromePass to other language, follow the
instructions below:
1. Run ChromePass with /savelangfile parameter:
   ChromePass.exe /savelangfile
   A file named ChromePass_lng.ini will be created in the folder of
   ChromePass utility.
2. Open the created language file in Notepad or in any other text
   editor.
3. Translate all string entries to the desired language. Optionally,
   you can also add your name and/or a link to your Web site.
   (TranslatorName and TranslatorURL values) If you add this information,
   it'll be used in the 'About' window.
4. After you finish the translation, Run ChromePass, and all
   translated strings will be loaded from the language file.
   If you want to run ChromePass without the translation, simply rename
   the language file, or move it to another folder.



License
=======

This utility is released as freeware. You are allowed to freely
distribute this utility via floppy disk, CD-ROM, Internet, or in any
other way, as long as you don't charge anything for this. If you
distribute this utility, you must include all files in the distribution
package, without any modification !



Disclaimer
==========

The software is provided "AS IS" without any warranty, either expressed
or implied, including, but not limited to, the implied warranties of
merchantability and fitness for a particular purpose. The author will not
be liable for any special, incidental, consequential or indirect damages
due to loss of data or any other reason.



Feedback
========

If you have any problem, suggestion, comment, or you found a bug in my
utility, you can send a message to nirsofer@yahoo.com

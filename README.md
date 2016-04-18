Have you ever wanted to use more than one application on your HTPC to access your media? Annoyed by Kodi's inability to ignore LIRC while it's in the background? Me too. 

LircLauncher allows you to set up applications to launch via their .desktop files that are installed with most Linux applications, and also supports custom apps for everything else. Just set it to launch on login, and you can finally have a perfect HTPC!

Installation
----

- `git clone https://github.com/magmastonealex/LircLauncher`
- Edit the settings.config file. Each line contains either the name of an application's .desktop file (without the extension), or something of the form Custom:Name:Exec Path:IconPath. Custom remains constant, but Name, Exec Path, and IconPath can be whatever fits your use case. A Chrome launcher script that also runs irexec & irxevent is included, and might be helpful for Netflix use.
- Edit lircrc to set up the buttons that the app uses. The example includes all useful commands.


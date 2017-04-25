#! /usr/bin/env python3 -OO

# Make sure the right Gtk version is loaded
import gi
gi.require_version('Gtk', '3.0')

import sys
from dialogs import ErrorDialog
from gi.repository import Gtk, GObject
from usbcreator import USBCreator


# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('usb-creator')


def uncaught_excepthook(*args):
    sys.__excepthook__(*args)
    if __debug__:
        from pprint import pprint
        from types import BuiltinFunctionType, ClassType, ModuleType, TypeType
        tb = sys.last_traceback
        while tb.tb_next: tb = tb.tb_next
        print(('\nDumping locals() ...'))
        pprint({k:v for k,v in tb.tb_frame.f_locals.items()
                    if not k.startswith('_') and
                       not isinstance(v, (BuiltinFunctionType,
                                          ClassType, ModuleType, TypeType))})
        if sys.stdin.isatty() and (sys.stdout.isatty() or sys.stderr.isatty()):
            try:
                import ipdb as pdb  # try to import the IPython debugger
            except ImportError:
                import pdb as pdb
            print(('\nStarting interactive debug prompt ...'))
            pdb.pm()
    else:
        import traceback
        details = '\n'.join(traceback.format_exception(*args)).replace('<', '').replace('>', '')
        title = _('Unexpected error')
        msg = _('USB Creator has failed with the following unexpected error. Please submit a bug report!')
        ErrorDialog(title, "<b>%s</b>" % msg, "<tt>%s</tt>" % details, None, True, 'usb-creator')

    sys.exit(1)

sys.excepthook = uncaught_excepthook

# main entry
if __name__ == "__main__":
    # Create an instance of our GTK application
    try:
        # Calling GObject.threads_init() is not needed for PyGObject 3.10.2+
        # Check with print (sys.version)
        # Debian Jessie: 3.4.2
        GObject.threads_init()

        USBCreator()
        Gtk.main()
    except KeyboardInterrupt:
        pass

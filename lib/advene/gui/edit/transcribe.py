"""Transcription view.
"""

import sys
import sre

import pygtk
import gtk
import gobject

import advene.core.config as config

# Advene part
from advene.model.package import Package
from advene.model.annotation import Annotation, Relation
from advene.model.schema import Schema, AnnotationType, RelationType

import advene.util.importer

import advene.util.vlclib as vlclib

from gettext import gettext as _

import advene.gui.edit.elements
import advene.gui.edit.create
import advene.gui.popup
import advene.gui.util

class TranscriptionImporter(advene.util.importer.GenericImporter):
    """Transcription importer.
    """
    def __init__(self, transcription_edit=None, **kw):
        super(TranscriptionImporter, self).__init__(**kw)
        self.transcription_edit=transcription_edit
        self.name = _("Transcription importer")

    def process_file(self, filename):
        if filename != 'transcription':
            return None
        if self.package is None:
            self.init_package()
        self.convert(self.transcription_edit.parse_transcription())
        return self.package

class TranscriptionEdit:
    def __init__ (self, controller=None):
        self.controller=controller
        self.package=controller.package
        self.tooltips=gtk.Tooltips()

        self.sourcefile=""
        self.empty_re = sre.compile('^\s*$')
        
        self.timestamp_mode_toggle=gtk.ToggleToolButton()
        self.timestamp_mode_toggle.set_label(_("Timestamps"))
        self.timestamp_mode_toggle.set_stock_id(gtk.STOCK_INDEX)
        self.timestamp_mode_toggle.set_active (True)
        self.timestamp_mode_toggle.set_tooltip(self.tooltips,
                                               _("If unchecked, allows to edit text"))
        
        # Discontinuous is True by default
        self.discontinuous_toggle=gtk.ToggleToolButton()
        self.discontinuous_toggle.set_label(_("Discontinuous"))
        self.discontinuous_toggle.set_active (True)
        self.discontinuous_toggle.set_stock_id(gtk.STOCK_REMOVE)
        self.discontinuous_toggle.set_tooltip(self.tooltips,
                                              _("Do not generate annotations for empty text"))
                    
        self.default_color = gtk.gdk.color_parse ('lightblue')
        self.ignore_color = gtk.gdk.color_parse ('tomato')

        self.widget=self.build_widget()

    def build_widget(self):
        vbox = gtk.VBox()
        
        self.textview = gtk.TextView()
        # We could make it editable and modify the annotation
        self.textview.set_editable(True)
        self.textview.set_wrap_mode (gtk.WRAP_CHAR)

        self.textview.connect("button-press-event", self.button_press_event_cb)

        vbox.add(self.textview)
        vbox.show_all()
        return vbox

    def remove_anchor(self, button, anchor, b):
        begin=b.get_iter_at_child_anchor(anchor)
        end=begin.copy()
        end.forward_char()
        b.delete_interactive(begin, end, True)
        button.destroy()
        return True
    
    def button_press_event_cb(self, textview, event):
        if event.button != 1:
            return False
        if not self.timestamp_mode_toggle.get_active():
            return False
        textwin=textview.get_window(gtk.TEXT_WINDOW_TEXT)
        if event.window != textwin:
            print "Event.window: %s" % str(event.window)
            print "Textwin: %s" % str(textwin)
            return False

        (x, y) = textview.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT,
                                                  int(event.x),
                                                  int(event.y))
        it=textview.get_iter_at_location(x, y)
        if it is None:
            print "Error in get_iter_at_location"
            return False

        p=self.controller.player
        if (p.status == p.PlayingStatus or p.status == p.PlayingStatus):
            self.create_timestamp_mark(p.current_position_value - config.data.reaction_time,
                                       it)
        return False

    def set_color(self, button, color):
        for style in (gtk.STATE_ACTIVE, gtk.STATE_NORMAL,
                      gtk.STATE_SELECTED, gtk.STATE_INSENSITIVE,
                      gtk.STATE_PRELIGHT):
            button.modify_bg (style, color)

    def toggle_ignore(self, button):
        if button.ignore:
            button.ignore=False
            self.set_color(button, self.default_color)
        else:
            button.ignore=True
            self.set_color(button, self.ignore_color)
        return
    
    def mark_button_press_cb(self, button, event):
        """Handler for right-button click on timestamp mark.
        """
        if event.button != 3:
            return False
        timestamp=button.timestamp
        # Create a popup menu for timestamp
        menu = gtk.Menu()

        def popup_goto (win, position):
            c=self.controller
            pos = c.create_position (value=position,
                                     key=c.player.MediaTime,
                                     origin=c.player.AbsolutePosition)
            c.update_status (status="set", position=pos)
            return True

        def popup_modify(win, child, t):
            timestamp=child.timestamp + t
            self.tooltips.set_tip(child, "%s" % vlclib.format_time(timestamp))
            child.timestamp=timestamp
            return True

        def popup_ignore(win, button):
            self.toggle_ignore(button)
            return True
        
        item = gtk.MenuItem(_("Position %s") % vlclib.format_time(timestamp))
        menu.append(item)

        item = gtk.SeparatorMenuItem()
        menu.append(item)

        item = gtk.MenuItem(_("Go to..."))
        item.connect("activate", popup_goto, timestamp)
        menu.append(item)

        item = gtk.MenuItem(_("Ignore the following text (toggle)"))
        item.connect("activate", popup_ignore, button)
        menu.append(item)
        
        item = gtk.MenuItem(_("-1 sec"))
        item.connect("activate", popup_modify, button, -1000)
        menu.append(item)
        item = gtk.MenuItem(_("-0.5 sec"))
        item.connect("activate", popup_modify, button, -500)
        menu.append(item)
        item = gtk.MenuItem(_("-0.1 sec"))
        item.connect("activate", popup_modify, button, -100)
        menu.append(item)
            
        item = gtk.MenuItem(_("+1 sec"))
        item.connect("activate", popup_modify, button, 1000)
        menu.append(item)
        item = gtk.MenuItem(_("+0.5 sec"))
        item.connect("activate", popup_modify, button, 500)
        menu.append(item)
        item = gtk.MenuItem(_("+0.1 sec"))
        item.connect("activate", popup_modify, button, 100)
        menu.append(item)
            
        menu.show_all()
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True
    
    def create_timestamp_mark(self, timestamp, it):
        b=self.textview.get_buffer()
        anchor=b.create_child_anchor(it)
        # Create the mark representation
        child=gtk.Button("")
        child.connect("clicked", self.remove_anchor, anchor, b)
        child.connect("button-press-event", self.mark_button_press_cb)
        self.tooltips.set_tip(child, "%s" % vlclib.format_time(timestamp))
        child.timestamp=timestamp
        child.ignore=False
        self.set_color(child, self.default_color)
        child.show()
        self.textview.add_child_at_anchor(child, anchor)
        return
        
    def populate(self, annotations):
        """Populate the buffer with data taken from the given annotations.
        """
        b=self.textview.get_buffer()
        # Clear the buffer
        begin,end=b.get_bounds()
        b.delete(begin, end)
        # FIXME: check for conflicting bounds
        l=[ (a.fragment.begin, a.fragment.end, a)
            for a in annotations ]
        l.sort(lambda a,b: cmp(a[0], b[0]))
        for (b, e, a) in l:
            it=b.get_iter_at_mark(b.get_insert())
            self.create_timestamp_mark(b, it)
            b.insert_at_cursor(unicode(a.content.data))
            it=b.get_iter_at_mark(b.get_insert())
            self.create_timestamp_mark(e, it)
        return            
        
    def parse_transcription(self):
        """Parse the transcription text.

        Return : a iterator on a dict with keys
        'begin', 'end', 'content' 
        (compatible with advene.util.importer)
        """

        t=0
        b=self.textview.get_buffer()
        begin=b.get_start_iter()
        end=begin.copy()
        ignore_next=False
        while end.forward_char():
            a=end.get_child_anchor()
            if a and a.get_widgets():
                # Found a TextAnchor
                child=a.get_widgets()[0]
                timestamp=child.timestamp
                text=b.get_text(begin, end, include_hidden_chars=False)
                text=text.rstrip().lstrip()
                if (self.discontinuous_toggle.get_active() and
                    self.empty_re.match(text)):
                    pass
                elif ignore_next:
                    pass
                else:
                    yield { 'begin': t,
                            'end':   timestamp,
                            'content': text }
                ignore_next=child.ignore                    
                t=timestamp
                begin=end.copy()
        # End of buffer. Create the last annotation
        timestamp=self.controller.player.stream_duration
        text=b.get_text(begin, end, include_hidden_chars=False)
        if (self.discontinuous_toggle.get_active() and
            self.empty_re.match(text)):
            pass
        elif ignore_next:
            pass
        else:
            yield { 'begin': t,
                    'end': timestamp,
                    'content': text }
        
    def save_transcription(self, button=None):
        fname=advene.gui.util.get_filename(title= ("Save transcription to..."),
                                           action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                           button=gtk.STOCK_SAVE)
        if fname is not None:
            self.save_output(filename=fname)
        return True

    def save_output(self, filename=None):
        f=open(filename, "w")
        last=None
        for d in self.parse_transcription():
            if last != d['begin']:
                f.writelines( ( '[%s]' % vlclib.format_time(d['begin']),
                                d['content'],
                                '[%s]' % vlclib.format_time(d['end']) ) )
            else:
                f.writelines( ( d['content'],
                                '[%s]' % vlclib.format_time(d['end']) ) )
            last=d['end']
        f.close()
        self.controller.log(_("Transcription saved to %s") % filename)
        return True
    
    def load_transcription_cb(self, button=None):
        fname=advene.gui.util.get_filename(title=_("Select transcription file to load"))
        if fname is not None:
            self.load_transcription(filename=fname)
        return True

    def load_transcription(self, filename=None):
        b=self.textview.get_buffer()
        begin,end=b.get_bounds()
        b.delete(begin, end)
        
        try:
            f=open(filename, 'r')
        except Exception, e:
            self.controller.log(_("Cannot read %s: %s") % (filename, str(e)))
            return
        data=unicode("".join(f.readlines()))
        self.sourcefile=filename
        
        mark_re=sre.compile('([^\]]*)\[(\d+:\d+:\d+.?\d*)\]')
        for m in mark_re.finditer(data):
            text, timestamp = m.group(1,2)
            t=vlclib.convert_time(timestamp)
            b.insert_at_cursor(text)
            it=b.get_iter_at_mark(b.get_insert())
            self.create_timestamp_mark(t, it)
        return

    def convert_transcription_cb(self, button=None):
        print "convert transcription"
        if not self.controller.gui:
            self.controller.log(_("Cannot convert the data : no associated package"))
            return True

        at=self.controller.gui.ask_for_annotation_type(text=_("Select the annotation type to generate"), create=True)

        if at is None:
            self.controller.log(_("Conversion cancelled"))
            return True

        ti=TranscriptionImporter(package=self.controller.package,
                                 controller=self.controller,
                                 defaulttype=at,
                                 transcription_edit=self)
        ti.process_file('transcription')

        self.controller.modified=True
        self.controller.notify("PackageLoad", package=ti.package)
        self.controller.log(_('Converted from file %s :') % self.sourcefile)
        self.controller.log(ti.statistics_formatted())
        # Feedback
        dialog = gtk.MessageDialog(
            None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE,
            _("Conversion completed.\n%s annotations generated.") % ti.statistics['annotation'])
        response=dialog.run()
        dialog.destroy()
        
        return True
    
    def get_widget (self):
        """Return the TreeView widget."""
        return self.widget

    def get_toolbar(self, window):
        tb=gtk.Toolbar()
        tb.set_style(gtk.TOOLBAR_ICONS) 
        radiogroup_ref=None

        tb_list = (
            (_("Open"), _("Open"), gtk.STOCK_OPEN, self.load_transcription_cb),
            (_("Save"), _("Save"), gtk.STOCK_SAVE, self.save_transcription),
            (_("Convert"), _("Convert"), gtk.STOCK_CONVERT, self.convert_transcription_cb),
            (_("Close"), _("Close"), gtk.STOCK_CLOSE, lambda w: window.destroy()),
            )

        for text, tooltip, icon, callback in tb_list:
            b=gtk.ToolButton(label=text)
            b.set_stock_id(icon)
            b.set_tooltip(self.tooltips, tooltip)
            b.connect("clicked", callback)
            tb.insert(b, -1)

        tb.insert(self.timestamp_mode_toggle, -1)
        tb.insert(self.discontinuous_toggle, -1)
            
        tb.show_all()
        return tb
    
    def popup(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        if self.controller.gui:
            self.controller.gui.init_window_size(window, 'transcribeview')

        window.set_title (_("Transcription alignment"))

        vbox = gtk.VBox()

        hb=gtk.HBox()
        vbox.pack_start(hb, expand=False)
        if self.controller.gui:
            toolbar=self.controller.gui.get_player_control_toolbar()
            hb.add(toolbar)
        hb.add(self.get_toolbar(window))

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        vbox.add (sw)
        sw.add_with_viewport (self.get_widget())
        if self.controller.gui:
            self.controller.gui.register_view (self)
            window.connect ("destroy", self.controller.gui.close_view_cb,
                            window, self)

        window.add(vbox)

        window.show_all()
        return window

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Should provide a package name"
        sys.exit(1)

    class DummyController:
        def log(self, *p):
            print p
            
        def notify(self, *p, **kw):
            print "Notify %s %s" % (p, kw)

            
    controller=DummyController()
    controller.gui=None

    import advene.player.dummy
    player=advene.player.dummy.Player()
    controller.player=player
    controller.player.status=controller.player.PlayingStatus
    
    #controller.package = Package (uri=sys.argv[1])
    config.data.path['resources']='/usr/local/src/advene-project/share'
    controller.package = Package (uri="new_pkg",
                            source=config.data.advenefile(config.data.templatefilename))

    transcription = TranscriptionEdit(controller=controller)

    window = transcription.popup()

    window.connect ("destroy", lambda e: gtk.main_quit())

    gtk.main ()


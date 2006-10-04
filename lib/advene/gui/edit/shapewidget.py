#
# This file is part of Advene.
#
# Advene is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Advene is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""Simple Shape editor widget
==========================

  This component provides a simple framework allowing to edit basic
  shapes, and generate the corresponding XML.

  This component should not have dependencies on Advene, so that it
  can be reused in other projects.

  FIXME

     - implement text shape ?
     - implement SVG import (with constraints)
"""

import gtk
import pango
from math import sqrt

import gettext
gettext.install('advene', unicode=True)

COLORS = [ 'red', 'green', 'blue', 'black', 'white' ]

class Shape:
    """The generic Shape class.

    @ivar name: the shape instance name
    @type name: string
    @ivar color: the shape color
    @type color: string
    @ivar linewidth: the line width
    @type linewidth: int
    @ivar filled: should the shape be filled ?
    @type filled: boolean
    @ivar tolerance: pixel tolerance for control point selection
    @type tolerance: int
    @cvar SHAPENAME: the name of the shape class
    @type SHAPENAME: translated string
    """

    SHAPENAME=_("Generic shape")

    def __init__(self, name=SHAPENAME, color="green"):
        self.name=name
        self.color=color
        self.linewidth=2
        self.filled = False
        # Pixel tolerance for control point selection
        self.tolerance = 6
        self.set_bounds( ( (0, 0), (10, 10) ) )

    def set_bounds(self, bounds):
        """Set the bounds of the shape.

        The bounds are the coordinates of the rectangular selection
        used to define the shape.

        @param bounds: a tuple of 2 int couples
        @type bounds: tuple
        """
        pass

    def get_bounds(self):
        """Return the bounds of the shape.

        @return: a tuple of 2 int couples
        @rtype: tuple
        """
        return ( (0, 0), (10, 10) )

    def render(self, pixmap, invert=False):
        """Render the shape on the given pixmap.

        @param pixmap: the destination pixmap
        @type pixmap: gtk.gdk.Pixmap
        @param invert: should the rendering inverse the selection ?
        @type invert: boolean
        """
        return

    def translate(self, vector):
        """Translate the shape.

        @param vector: the translation vector
        @type vector: a couple of int
        """
        pass

    def control_point(self, point):
        """Test if the given point is a control point.

        If on a control point, return its coordinates (x, y) and those of the
        other bound, else None

        @param point: the tested point
        @type point: a couple of int
        @return: None, or a couple of coordinates
        @rtype: tuple
        """
        return None

    def __contains__(self, point):
        """Test if the given point is inside the shape.

        @param point: the tested point
        @type point: a couple of int
        @rtype: boolean
        """
        return False

    def get_svg(self, relative=False, size=None):
        """Return a SVG representation of the shape.

        @param relative: should dimensions be relative to the container size or absolute?
        @type relative: boolean
        @param size: the container size in pixels
        @type size: a couple of int
        @return: the SVG representation
        @rtype: string
        """
        return u"<text>Generic shape</text>"

    def copy_from(self, shape, style=False):
        """Copy data from another shape.

        @param shape: the original shape
        @param style: should the style be copied also?
        @type style: boolean
        """
        return

    def clone(self, style=False):
        """Clone the shape.

        @param style: should the style be copied also?
        @type style: boolean
        @return: a new shape
        """
        s=self.__class__()
        s.copy_from(self, style)
        return s

    def edit_properties_widget(self):
        """Build a widget to edit the shape properties.
        """
        vbox=gtk.VBox()

        def label_widget(label, widget):
            hb=gtk.HBox()
            hb.add(gtk.Label(label))
            hb.pack_start(widget, expand=False)
            return hb

        # Name
        namesel = gtk.Entry()
        namesel.set_text(self.name)
        vbox.pack_start(label_widget(_("Name"), namesel), expand=False)

        # Color
        colorsel = gtk.combo_box_new_text()
        for s in COLORS:
            colorsel.append_text(s)
        try:
            i=COLORS.index(self.color)
        except IndexError:
            i=0
        colorsel.set_active(i)
        vbox.pack_start(label_widget(_("Color"), colorsel), expand=False)

        # Linewidth
        linewidthsel = gtk.SpinButton()
        linewidthsel.set_range(1, 15)
        linewidthsel.set_increments(1,1)
        linewidthsel.set_value(self.linewidth)
        vbox.pack_start(label_widget(_("Linewidth"), linewidthsel), expand=False)

        # Filled
        filledsel = gtk.ToggleButton()
        filledsel.set_active(self.filled)
        vbox.pack_start(label_widget(_("Filled"), filledsel), expand=False)

        vbox.widgets = {
            'name': namesel,
            'color': colorsel,
            'linewidth': linewidthsel,
            'filled': filledsel
            }
        return vbox

    def edit_properties(self):
        """Display a widget to edit the shape properties.
        """
        edit=self.edit_properties_widget()

        d = gtk.Dialog(title=_("Properties of %s") % self.name,
                       parent=None,
                       flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons=( gtk.STOCK_OK, gtk.RESPONSE_OK,
                                 gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL ) )

        d.vbox.add(edit)

        def keypressed_cb(widget=None, event=None):
            if event.keyval == gtk.keysyms.Return:
                d.response(gtk.RESPONSE_OK)
                return True
            elif event.keyval == gtk.keysyms.Escape:
                d.response(gtk.RESPONSE_CANCEL)
                return True
            return False
        d.connect("key_press_event", keypressed_cb)

        edit.show_all()
        res=d.run()
        d.destroy()

        if res == gtk.RESPONSE_OK:
            # Get new values
            self.name = edit.widgets['name'].get_text()
            self.color = COLORS[edit.widgets['color'].get_active()]
            self.linewidth = int(edit.widgets['linewidth'].get_value())
            self.filled = edit.widgets['filled'].get_active()
            return True

        return False

class Rectangle(Shape):
    """Rectangle shape.

    It can be used as a baseclass for other shapes with corresponding
    behaviour.
    """
    SHAPENAME=_("Rectangle")

    def set_bounds(self, bounds):
        self.x = int(min(bounds[0][0], bounds[1][0]))
        self.y = int(min(bounds[0][1], bounds[1][1]))
        self.width = int(abs(bounds[0][0] - bounds[1][0]))
        self.height = int(abs(bounds[0][1] - bounds[1][1]))

    def get_bounds(self):
        return ( (self.x, self.y), (self.x + self.width, self.y + self.height) )

    def render(self, pixmap, invert=False):
        col=pixmap.get_colormap().alloc_color(self.color)
        gc=pixmap.new_gc(foreground=col, line_width=self.linewidth)
        if invert:
            gc.set_function(gtk.gdk.INVERT)
        pixmap.draw_rectangle(gc,
                  self.filled,
                  self.x,
                  self.y,
                  self.width,
                  self.height)
        return

    def translate(self, vector):
        self.x += int(vector[0])
        self.y += int(vector[1])

    def copy_from(self, shape, style=False):
        shape.x = self.x
        shape.y = self.y
        shape.width = self.width
        shape.height = self.height
        if style:
            shape.color = self.color
            shape.linewidth = self.linewidth

    def control_point(self, point):
        """If on a control point, return its coordinates (x, y) and those of the other bound, else None

        This version is fitted for rectangular areas
        """
        x, y = point[0], point[1]
        retval = [[None, None], [None, None]]
        if abs(x - self.x) <= self.tolerance:
            retval[0][0] = self.x + self.width
            retval[1][0] = self.x
        elif abs(x - self.x - self.width) <= self.tolerance:
            retval[0][0] = self.x
            retval[1][0] = self.x + self.width
        else:
            return None
        if abs(y - self.y) <= self.tolerance:
            retval[0][1] = self.y + self.height
            retval[1][1] = self.y
        elif abs(y - self.y - self.height) <= self.tolerance:
            retval[0][1] = self.y
            retval[1][1] = self.y + self.height
        else:
            return None
        return retval

    def __contains__(self, point):
        x, y = point
        return ( x >= self.x
                 and x <= self.x + self.width
                 and y >= self.y
                 and y <= self.y + self.height )

    def get_svg(self, relative=False, size=None):
        if relative and size:
            pos="""x="%d%%" y="%d%%" width="%d%%" height="%d%%" """ % (
                self.x * 100 / size[0],
                self.y * 100 / size[1],
                self.width * 100 / size[0],
                self.height * 100 / size[1] )
        else:
            pos="""x="%d" y="%d" width="%d" height="%d" """ % (
                self.x,
                self.y,
                self.width,
                self.height )

        if self.filled:
            fill=self.color
        else:
            fill='none'

        return """<rect %s fill="%s" stroke="%s" style="stroke-width:%s" />""" % (
            pos, fill, self.color, str(self.linewidth) )

class Text(Rectangle):
    """Experimental Text shape. Non-working for the moment.
    """
    SHAPENAME=_("Text")

    def render(self, pixmap, invert=False):
        col=pixmap.get_colormap().alloc_color(self.color)
        gc=pixmap.new_gc(foreground=col, line_width=self.linewidth)
        if invert:
            gc.set_function(gtk.gdk.INVERT)
        l=pango.Layout(pango.Context())
        l.set_text(self.name)
        self.width, self.height = l.get_pixel_size()
        pixmap.draw_layout(gc,
                           self.x,
                           self.y,
                           l)
        return

    def get_svg(self, relative=False, size=None):
        """Return a SVG representation of the shape.
        """
        if relative and size:
            size="""x="%d%%" y="%d%%" """ % (
                self.x * 100 / size[0],
                self.y * 100 / size[1] )
        else:
            size="""x="%d" y="%d" """ % (
                self.x,
                self.y )

        return """<text %s stroke="%s" style="stroke-width:%s" />%s</text>""" % (
            size, self.color, str(self.linewidth), self.name )

class Line(Rectangle):
    """A simple Line.
    """
    SHAPENAME=_("Line")

    def set_bounds(self, bounds):
        self.x1, self.y1 = bounds[0]
        self.x2, self.y2 = bounds[1]

        self.width = int(self.x2 - self.x1)
        self.height = int(self.y2 - self.y1)

    def get_bounds(self):
        return ( (self.x1, self.y1), (self.x2, self.y2 ) )

    def render(self, pixmap, invert=False):
        col=pixmap.get_colormap().alloc_color(self.color)
        gc=pixmap.new_gc(foreground=col, line_width=self.linewidth)
        if invert:
            gc.set_function(gtk.gdk.INVERT)
        pixmap.draw_line(gc,
                  self.x1,
                  self.y1,
                  self.x2,
                  self.y2)
        return

    def translate(self, vector):
        self.x1 += int(vector[0])
        self.x2 += int(vector[0])
        self.y1 += int(vector[1])
        self.y2 += int(vector[1])
        # Recompute other attributes
        self.set_bounds( self.get_bounds() )

    def copy_from(self, shape, style=False):
        shape.set_bounds( self.get_bounds() )
        if style:
            shape.color = self.color
            shape.linewidth = self.linewidth

    def __contains__(self, point):
        x, y = point
        return False

    def get_svg(self, relative=False, size=None):
        """Return a SVG representation of the shape.
        """
        if relative and size:
            size="""x1="%d%%" y1="%d%%" x2="%d%%" y2="%d%%" """ % (
                self.x1 * 100 / size[0],
                self.y1 * 100 / size[1],
                self.x2 * 100 / size[0],
                self.y2 * 100 / size[1] )
        else:
            size="""x1="%d" y1="%d" x2="%d" y2="%d" """ % (
                self.x1,
                self.y1,
                self.x2,
                self.y2 )

        return """<line %s stroke="%s" style="stroke-width:%s" />""" % (
            size, self.color, str(self.linewidth) )

class Circle(Rectangle):
    """A Circle shape.

    @ivar centerx, centery: the coordinates of the center in pixel
    @type centerx, centery: int
    @ivar radius: the circle radius in pixel
    @type radius: int
    """
    SHAPENAME=_("Circle")

    def set_bounds(self, bounds):
        self.x = int(min(bounds[0][0], bounds[1][0]))
        self.y = int(min(bounds[0][1], bounds[1][1]))
        self.width = int(abs(bounds[0][0] - bounds[1][0]))
        self.height = int(abs(bounds[0][1] - bounds[1][1]))

        self.centerx = int( (bounds[0][0] + bounds[1][0]) / 2)
        self.centery = int( (bounds[0][1] + bounds[1][1]) / 2)
        self.radius = int(sqrt( (self.width / 2) ** 2 + (self.height / 2) ** 2))

    def render(self, pixmap, invert=False):
        col=pixmap.get_colormap().alloc_color(self.color)
        gc=pixmap.new_gc(foreground=col, line_width=self.linewidth)
        if invert:
            gc.set_function(gtk.gdk.INVERT)
        pixmap.draw_arc(gc,
                  self.filled,
                  self.x, self.y,
                  self.width, self.height,
                  0, 360 * 64)
        return

    def __contains__(self, point):
        x, y = point
        d = (point[0] - self.centerx) ** 2 + (point[1] - self.centery) ** 2
        return d <= ( self.radius ** 2 )

    def get_svg(self, relative=False, size=None):
        """Return a SVG representation of the shape.
        """
        if relative and size:
            size="""cx="%d%%" cy="%d%%" r="%d%%" """ % (
                self.centerx * 100 / size[0],
                self.centery * 100 / size[1],
                self.radius * 100 / size[0] )
        else:
            size="""cx="%d" cy="%d" r="%d" """ % (
                self.centerx,
                self.centery,
                self.radius )

        if self.filled:
            fill=self.color
        else:
            fill='none'

        return """<circle %s fill="%s" stroke="%s" style="stroke-width:%s" />""" % (
            size, fill, self.color, str(self.linewidth) )

class ShapeDrawer:
    """Widget allowing to draw and edit shapes.

    @ivar callback: method called when the button is released.
    @type callback: method taking a rectangle as parameter

    @ivar background: the canvas background
    @type background: gtk.Image
    @ivar objects: the list of defined objects
    @type objects: gtk.ListStore
    @ivar selection: the rectangular selection coordinates
    @type selection: a list of 2 lists
    @ivar feedback_shape: the currently edited shape, displayed as feedback
    @type feedback_shape: Shape
    @ivar shape_class: the default shape class to be created

    @ivar mode: the current editing mode ("create", "resize" or "translate")
    @type mode: string

    @ivar pixmap: the edited pixmap
    @type pixmap: gtk.gdk.Pixmap
    @ivar canvaswidth, canvasheight: the canvas dimensions
    @type canvaswidth, canvasheight: int

    @ivar widget: the gtk Widget for the component
    @type widget: gtk.Widget

    """
    def __init__(self, callback=None, background=None):
        """
        @param callback: the callback method
        @param background: an optional background image
        @type background: gtk.Image
        """
        self.callback = callback or self.default_callback

        # background is a gtk.Image()
        self.background = background

        # Couples object - name
        self.objects = gtk.ListStore( object, str )

        # Marked area point[0, 1][x, y]
        self.selection = [[None, None], [None, None]]
        self.feedback_shape = None
        self.shape_class = Rectangle

        # mode: "create", "resize" or "translate"
        self.mode = "resize"

        self.pixmap = None

        self.widget = gtk.DrawingArea()
        self.widget.connect("expose_event", self.expose_event)
        self.widget.connect("configure_event", self.configure_event)
        self.widget.connect("button_press_event", self.button_press_event)
        self.widget.connect("button_release_event", self.button_release_event)
        self.widget.connect("motion_notify_event", self.motion_notify_event)
        self.widget.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK |gtk.gdk.POINTER_MOTION_HINT_MASK)

        if self.background:
            p=self.background.get_pixbuf()
            w=p.get_width()
            h=p.get_height()
            self.widget.set_size_request(w, h)
            self.canvaswidth=w
            self.canvasheight=h

    def default_callback(self, rectangle):
        """Default callback.
        """
        print "Got selection ", str(rectangle)

    def add_object(self, o):
        """Add an object (shape) to the object list.
        """
        self.objects.append( (o, o.name) )
        self.plot()

    def find_object(self, o):
        """Return the iterator for the given object.

        @param o: the searched object
        @return: the iterator
        @rtype: gtk.Iterator
        """
        i = self.objects.get_iter_first()
        while i is not None:
            if self.objects.get_value(i, 0) == o:
                return i
            i = self.objects.iter_next(i)
        return None

    def remove_object(self, o):
        """Remove the given object from the list.
        """
        i = self.find_object(o)
        if i is not None:
            self.objects.remove( i )
        self.plot()

    def dimensions(self):
        """Return the canvas dimensions.

        @return: the dimensions in pixel
        @rtype: a couple (width, height)
        """
        return (self.canvaswidth, self.canvasheight)

    def configure_event(self, widget, event):
        if self.background:
            p=self.background.get_pixbuf()
            w=p.get_width()
            h=p.get_height()
        else:
            x, y, w, h = widget.get_allocation()

        self.pixmap = gtk.gdk.Pixmap(widget.window, w, h)
        self.canvaswidth = w
        self.canvasheight = h
        self.plot()
        return True

    # Redraw the screen from the backing pixmap
    def expose_event(self, widget, event):
        x, y, w, h = event.area
        widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL], self.pixmap, x, y, x, y, w, h)
        return False

    def clicked_shape(self, point):
        """Check if point is on a shape.
        """
        for o in self.objects:
            if point in o[0]:
                return o[0]
        return None

    def add_menuitem(self, menu=None, item=None, action=None, *param, **kw):
        if item is None or item == "":
            i = gtk.SeparatorMenuItem()
        else:
            i = gtk.MenuItem(item)
        if action is not None:
            i.connect("activate", action, *param, **kw)
        menu.append(i)

    def popup_menu(self, shape):
        menu = gtk.Menu()

        def add_item(*p, **kw):
            self.add_menuitem(menu, *p, **kw)

        def remove(i, o):
            self.remove_object(o)

        def properties(i, o):
            if o.edit_properties():
                self.plot()
                # Update liststore
                i = self.find_object(o)
                if i is not None:
                    self.objects.set_value(i, 1, o.name)

        def dump_svg(i, o):
            print o.get_svg()
            return True

        add_item(shape.name)
        add_item("")
        add_item(_("Delete"), remove, shape)
        add_item(_("Properties"), properties, shape)
        add_item(_("SVG"), dump_svg, shape)

        menu.show_all()
        menu.popup(None, None, None, 0, gtk.get_current_event_time())

        return True

    # Start marking selection
    def button_press_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        if event.button == 1:
            self.selection[0][0], self.selection[0][1] = x, y
            self.selection[1][0], self.selection[1][1] = None, None
            sel=self.clicked_shape( ( x, y ) )
            if sel is not None:
                # Existing shape selected
                self.feedback_shape = sel
                c=sel.control_point( (x, y) )
                if c is not None:
                    self.selection = c
                    self.mode = "resize"
                else:
                    self.mode = "translate"
            else:
                self.feedback_shape = self.shape_class()
                self.feedback_shape.set_bounds( ( self.selection[0], self.selection[0]) )
                self.mode = "create"
        elif event.button == 3:
            # Popup menu
            sel=self.clicked_shape( ( x, y ) )
            if sel is not None:
                self.popup_menu(sel)
        return True

    # End of selection
    def button_release_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)

        retval = ( self.selection[0][:], self.selection[1][:])
        if event.button == 1:
            if self.feedback_shape is not None:
                self.feedback_shape = None
                self.plot()

            self.selection[1][0] = None
            self.selection[0][0] = None

            if self.mode == "create":
                self.callback( retval )

    # Draw rectangle during mouse movement
    def motion_notify_event(self, widget, event):
        if event.is_hint:
            x, y, State = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            State = event.state

        if State & gtk.gdk.BUTTON1_MASK and self.feedback_shape is not None:
            if self.selection[1][0] is not None:
                self.feedback_shape.render(self.pixmap, invert=True)
            self.selection[1][0], self.selection[1][1] = int(x), int(y)

            if self.mode == "translate":
                self.feedback_shape.translate( (x - self.selection[0][0],
                                                y - self.selection[0][1] ) )
                self.selection[0][0] = x
                self.selection[0][1] = y
            elif self.mode == "resize" or self.mode == "create":
                self.feedback_shape.set_bounds( self.selection )

            self.feedback_shape.render(self.pixmap, invert=True)
            self.draw_drawable()

    def draw_drawable(self):
        """Render the pixmap in the drawingarea."""
        x, y, w, h = self.widget.get_allocation()
        self.widget.window.draw_drawable(self.widget.get_style().fg_gc[gtk.STATE_NORMAL], self.pixmap, 0, 0, 0, 0, w, h)

    def plot(self):
        """Draw in the pixmap.
        """
        if self.pixmap is None:
            return
        self.pixmap.draw_rectangle(self.widget.get_style().white_gc, True, 0, 0, self.canvaswidth, self.canvasheight)

        if self.background:
            pixbuf=self.background.get_pixbuf()
            self.pixmap.draw_pixbuf(self.widget.get_style().white_gc,
                                    pixbuf,
                                    0, 0,
                                    0, 0)

        for o in self.objects:
            o[0].render(self.pixmap)

        if self.feedback_shape is not None:
            self.feedback_shape.render(self.pixmap, invert=True)

        self.draw_drawable()

class ShapeEditor:
    """Shape Editor component.

    This component provides an example of using ShapeWidget.
    """
    def __init__(self, background=None):
        self.background=None
        self.drawer=ShapeDrawer(callback=self.callback,
                                background=background)
        self.shapes = [ Rectangle, Circle, Line ]

        self.colors = COLORS
        self.defaultcolor = self.colors[0]
        self.widget=self.build_widget()

    def callback(self, l):
        r = self.drawer.shape_class()
        r.name = r.SHAPENAME + str(l)
        r.color = self.defaultcolor
        r.set_bounds(l)
        self.drawer.add_object(r)
        return

    def remove_item(self, treeview, path, column):
        m=treeview.get_model()
        o=treeview.get_model()[m.get_iter(path)][0]
        self.drawer.remove_object(o)
        return True

    def build_selector(self, l, callback):
        sel = gtk.combo_box_new_text()
        for s in l:
            sel.append_text(s)
        sel.connect("changed", callback)
        sel.set_active(0)
        return sel

    def tree_view_button_cb(self, widget=None, event=None):
        retval = False
        button = event.button
        x = int(event.x)
        y = int(event.y)

        # On double-click, edit element
        if event.type == gtk.gdk._2BUTTON_PRESS:
            node = self.get_selected_node (widget)
            if node is not None:
                if node.edit_properties():
                    self.drawer.plot()
                    # Update liststore
                    i = self.drawer.find_object(node)
                    if i is not None:
                        self.drawer.objects.set_value(i, 1, node.name)
                retval=True
            else:
                retval=False
        elif button == 3:
            if event.window is widget.get_bin_window():
                model = widget.get_model()
                t = widget.get_path_at_pos(x, y)
                if t is not None:
                    path, col, cx, cy = t
                    it = model.get_iter(path)
                    node = model.get_value(it, 0)
                    widget.get_selection().select_path (path)
                    self.drawer.popup_menu(node)
                    retval = True
        return retval

    def build_widget(self):
        vbox=gtk.VBox()


        hbox=gtk.HBox()
        vbox.add(hbox)


        hbox.pack_start(self.drawer.widget, True, True, 0)

        self.treeview = gtk.TreeView(self.drawer.objects)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Name', renderer,
                                    text=1)
        self.treeview.append_column(column)
        self.treeview.connect('row_activated', self.remove_item)
        self.treeview.connect("button_press_event", self.tree_view_button_cb)

        control = gtk.VBox()

        # FIXME: toolbar at the top
        def changeshape(combobox):
            self.drawer.shape_class = self.shapes[combobox.get_active()]
            return True

        shapeselector = self.build_selector( [ s.SHAPENAME for s in self.shapes ],
                                            changeshape )
        control.pack_start(shapeselector, expand=False)

        def changecolor(combobox):
            self.defaultcolor = self.colors[combobox.get_active()]
            return True

        colorselector = self.build_selector( self.colors,
                                             changecolor )
        control.pack_start(colorselector, expand=False)

        control.pack_start(self.treeview, expand=False)

        def dump_svg(b):
            size=(self.drawer.canvaswidth, self.drawer.canvasheight)
            print """<svg version='1' preserveAspectRatio="xMinYMin meet" viewBox='0 0 %d %d'>""" % size
            for o in self.drawer.objects:
                print o[0].get_svg(relative=True, size=size)
            print """</svg>"""

        b=gtk.Button(_("Dump SVG"))
        b.connect("clicked", dump_svg)
        control.pack_start(b, expand=False)

        hbox.pack_start(control, expand=False)
        vbox.show_all()
        return vbox

def main():
    import sys

    if len(sys.argv) > 1:
        bg = sys.argv[1]
    else:
        bg = 'atelier.jpg'

    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    win.set_title("Shape Editor test")
    #win.set_default_size(800, 600)
    win.connect("delete-event", lambda w, e: gtk.main_quit())

    i=gtk.Image()
    i.set_from_file(bg)

    ed=ShapeEditor(background=i)
    win.add(ed.widget)

    win.show_all()

    gtk.main()


# Start it all
if __name__ == '__main__':
    main()

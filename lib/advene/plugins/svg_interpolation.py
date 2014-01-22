# -*- coding: utf-8 -*-
#
# Advene: Annotate Digital Videos, Exchange on the NEt
# Copyright (C) 2013 Olivier Aubert <contact@olivieraubert.net>
#
# Advene is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Advene is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Advene; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

from gettext import gettext as _
import xml.etree.ElementTree as ET
import StringIO
from itertools import izip

import gtk

import advene.core.config as config
from advene.gui.views import AdhocView
from advene.gui.edit.shapewidget import ShapeDrawer
from advene.gui.util.dialog import list_selector_widget, message_dialog

name = "SVG Interpolation"

def register(controller):
    controller.register_viewclass(SVGInterpolation)

    menu = controller.gui.gui.adhoc_view_menuitem.get_submenu()
    it=gtk.MenuItem(SVGInterpolation.view_name, use_underline=False)
    it.set_tooltip_text(SVGInterpolation.tooltip)
    def open_view(*p):
        controller.gui.open_adhoc_view(SVGInterpolation.view_id)
        return True
    it.connect('activate', open_view)
    menu.prepend(it)
    it.show_all()
    return True

class SVGInterpolation(AdhocView):
    view_name = _("SVG Interpolation")
    view_id = 'svg_interpolation'
    tooltip=_("SVG Interpolation")

    def __init__(self, controller=None, parameters=None):
        super(SVGInterpolation, self).__init__(controller=controller)
        self.close_on_package_load = False
        self.contextual_actions = [
            ]
        self.controller = controller
        self.registered_rules = []
        self.interval = config.data.preferences.get('svg-interpolation-interval', 500)
        self.widget = self.build_widget()

    def parse_annotations(self, at):
        """Parse annotations of a given type for their shapes.
        """
        if not 'svg' in at.mimetype:
            return []
        res = []
        for a in sorted(at.annotations, key=lambda e: e.fragment.begin):
            drawer = ShapeDrawer()
            drawer.parse_svg(ET.parse(a.content.stream).getroot())
            # Fix bug in ShapeDrawer wrt. dimension handling
            drawer.canvaswidth, drawer.canvasheight = drawer.svg_dimensions
            # Parse again to get correct dimensions
            drawer.clear_objects()
            drawer.parse_svg(ET.parse(a.content.stream).getroot())

            res.append({ 'annotation': a,
                         'begin': a.fragment.begin,
                         'end': a.fragment.end,
                         'drawer': drawer,
                         'objects': list(r[0] for r in drawer.objects) })
        return res

    def generate(self, source, destination, interval=None):
        def update_from_values(shape, values):
            for n, v in values.iteritems():
                setattr(shape, n, v)

        if interval is None:
            interval = config.data.preferences.get('svg-interpolation-interval', 500)
        if interval != config.data.preferences.get('svg-interpolation-interval'):
            config.data.preferences['svg-interpolation-interval'] = interval
            config.data.save_preferences()

        self.controller.notify('EditSessionStart', element=destination)

        # Delete all annotations from destination
        batch_id = object()
        for a in destination.annotations:
            self.controller.delete_element(a, batch=batch_id)

        # Copy origin annotation
        for a in source.annotations:
            self.controller.transmute_annotation(a, destination)

        # Number of processed "zones"
        zone_count = 0
        # Number of created annotations
        total_count = len(source.annotations)

        # Generate interpolated annotations
        datasets = self.parse_annotations(source)
        for (d1, d2) in zip(datasets[:-1], datasets[1:]):
            pos = d1['end']
            a = None
            for object_values in self.interpolate(d1, d2, interval):
                for (shape, values) in izip(d1['objects'], object_values):
                    update_from_values(shape, values)
                tree = ET.ElementTree(d1['drawer'].get_svg(relative=False))
                s = StringIO.StringIO()
                tree.write(s, encoding='utf-8')
                a = self.controller.create_annotation(pos, destination, duration=interval, content=s.getvalue())
                total_count += 1
                s.close()
                pos += interval
            # Set last created annotation end time to d2['begin']
            if a is not None:
                a.fragment.end = d2['begin']
                self.controller.notify('AnnotationEditEnd', annotation=a)
                zone_count += 1
        self.controller.notify('EditSessionEnd', element=destination)
        return zone_count, total_count

    def interpolate(self, d1, d2, interval=500):
        """Interpolate between 2 annotations info sets returned by parse_annotations

        Generate an annotation every interval ms.
        """
        if not d1['objects'] or len(d1['objects']) != len(d2['objects']):
            self.controller.log("Differing objects lengths")
            return []
        if any(d[0].SHAPENAME != d[1].SHAPENAME for d in zip(d1['objects'], d2['objects'])):
            return []

        def to_values(shape):
            return dict( (c[0], getattr(shape, c[0])) for c in shape.coords )

        num = (d2['begin'] - d1['end']) / interval
        if not num:
            return []

        return izip(*[self.interpolate_values(to_values(d1['objects'][i]),
                                            to_values(d2['objects'][i]),
                                            num)
                    for i in range(len(d1['objects']))])

    def interpolate_values(self, d1, d2, num=10):
        """Interpolate between 2 sets of coord/value dicts.

        d1 and d2 are assumed to contain the same keys.
        """
        steps = dict((n, (d2[n] - d1[n]) / float(num)) for n in d1)
        data = dict(d1)
        for n in range(num):
            data = dict( (n, int(data[n] + steps[n])) for n in d1 )
            yield data

    def build_widget(self):
        vbox = gtk.VBox()
        vbox.pack_start(gtk.Label("Interpolation SVG"), expand=False)

        hb = gtk.HButtonBox()
        vbox.pack_start(hb, expand=False)

        p = self.controller.package
        source = list_selector_widget(members=[ (at, at.title, self.controller.get_element_color(at))
                                                for at in p.annotationTypes ],
                                      preselect=p.get_element_by_id('rendu_expressif'),
                                      entry=False)
        destination = list_selector_widget(members=[ (at, at.title, self.controller.get_element_color(at))
                                                     for at in p.annotationTypes ],
                                           preselect=p.get_element_by_id('interpolation'),
                                           entry=False)
        interval = gtk.SpinButton()
        interval.set_range(25, 10000)
        interval.set_increments(100, 1000)
        interval.set_value(self.interval)

        def label_widget(label, widget):
            hb=gtk.HBox()
            hb.add(gtk.Label(label))
            hb.pack_start(widget, expand=False)
            return hb

        vbox.pack_start(label_widget(_("Interpolate annotations of type "), source), expand=False)
        vbox.pack_start(label_widget(_("Create annotations in type"), destination), expand=False)
        vbox.pack_start(label_widget(_("Annotation duration (in ms)"), interval), expand=False)

        def run_interpolation(item, s, d, i):
            zone_count, total = self.generate(s.get_current_element(), d.get_current_element(), interval=int(i.get_value()))
            message_dialog(_("Interpolation done.\n\n%d created annotations in %d ranges") % (total, zone_count))
            return True

        b = gtk.Button(_("Lancer l'interpolation"))
        b.connect("clicked", run_interpolation, source, destination, interval)
        vbox.pack_start(b, expand=False)

        vbox.show_all()
        return vbox

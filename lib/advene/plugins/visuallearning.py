#
# Advene: Annotate Digital Videos, Exchange on the NEt
# Copyright (C) 2008-2012 Olivier Aubert <olivier.aubert@liris.cnrs.fr>
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
# along with Advene; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

"""
This is a plugin developped for the Visual Learning (VL) project.
It exports as an HTML5 view a package using the VL annotation schema.
"""

from gettext import gettext as _

import gtk
import itertools
import json
import os
import re
import shutil
import subprocess
import urllib

import advene.core.config as config
from advene.gui.views import AdhocView
import advene.util.helper as helper

from advene.gui.util import dialog

from advene.plugins.visuallearning_files import CONTENTS

name = "Visual Learning panel"
NS = "http://omendo.fr/visuallearning/"

def register(controller):
    controller.register_viewclass(VisualLearningPanel)

    menu = controller.gui.gui.adhoc_view_menuitem.get_submenu()
    it=gtk.MenuItem(VisualLearningPanel.view_name, use_underline=False)
    it.set_tooltip_text(VisualLearningPanel.tooltip)
    def open_view(*p):
        controller.gui.open_adhoc_view(VisualLearningPanel.view_id)
        return True
    it.connect('activate', open_view)
    menu.prepend(it)
    it.show_all()
    return True

class VisualLearningPanel(AdhocView):
    view_name = _("Visual Learning panel")
    view_id = 'visual_learning_panel'
    tooltip=_("Visual Learning panel")

    def __init__(self, controller=None, parameters=None):
        super(VisualLearningPanel, self).__init__(controller=controller)
        self.close_on_package_load = False
        self.controller = controller
        #self.contextual_actions = []
        #self.registered_rules = []
        self.widget = self.build_widget()
        self.should_continue = False

    def get_original_and_expressive_media(self):
        pkg = self.controller.package
        original = pkg.getMetaData(NS, 'original-video')
        if original is None:
            original = self.controller.get_default_media(pkg) or None
            if original:
                pkg.setMetaData(NS, 'original-video', original)
                pkg._modified = True
        if original is not None:
            expressive = original + ".expressive.mp4"
        else:
            expressive = None
        return original, expressive

    def compute_exprender(self):
        original, expressive = self.get_original_and_expressive_media()
        return original is not None \
            and self.controller.get_default_media(self.controller.package) == expressive
        
    def toggle_exprender(self, b):
        self.set_exprender(b.get_active(), True)

    def set_exprender(self, val, from_gui=False):
        original, expressive = self.get_original_and_expressive_media()
        if original is not None:
            if val:
                self.controller.set_default_media(expressive)
            else:
                self.controller.set_default_media(original)
            self.controller.package._modified = True
            if not from_gui:
                self.exprender_toggle.set_active(val)
        else:
            if from_gui and val:
                dialog.message_dialog(_("No video is set"))
                self.exprender_toggle.set_active(False)
                

    def report_progress(self, val, msg):
        pb = self.progress_bar
        if not self.should_continue:
            raise AbortExport()
        if val >= 0 and val <= 1.0:
            pb.set_fraction(val)
        if len(msg) > 80:
            msg = msg[:36] + "(...)" + msg[-36:]
        pb.set_text(msg)
        # force the refresh of the progress bar
        while gtk.events_pending():
            gtk.main_iteration()

    def do_convert(self, b):
        pkg = self.controller.package
        original, expressive = self.get_original_and_expressive_media()
        if original is None:
            dialog.message_dialog(_("No video is set"))
            self.exprender_toggle.set_active(False)
            return

        self.export_button.set_sensitive(False)
        # force the refresh of the buttons
        while gtk.events_pending():
            gtk.main_iteration()
        try:
            vie = self.vie_entry.get_text()
            if not vie:
                raise Exception("VIE path not provided")
            filename = pkg.getUri()
            if filename.startswith("file:///"):
                filename = urllib.url2pathname(filename[7:])
            if pkg._modified:
                pkg.save()
            print "===", vie, filename, expressive
            status = subprocess.call('"%s" "%s" "%s"' % (vie, filename, expressive),
                                     stdout=None, stderr=None, shell=True)
            if status != 0:
                raise Exception("VIE exited with status %s" % status)
            self.set_exprender(True)
        except Exception, e:
            dialog.message_dialog(_("Could not convert to expressive rendering: ") + unicode(e),
                                  icon=gtk.MESSAGE_ERROR)
            import traceback; self.controller.log(traceback.format_exc())
        finally:
            b.set_sensitive(True)
            self.export_button.set_sensitive(True)

    def do_export(self, b):
        pkg = self.controller.package
        d=unicode(self.dirname_entry.get_text())
        if not d:
            dialog.message_dialog(_("No destination directory provided"),
                                  icon=gtk.MESSAGE_ERROR)
            return False

        vie=self.vie_entry.get_text() or None
        template = self.template_entry.get_text() or None
        exprender = self.exprender_toggle.get_active()
        browse = self.browse_toggle.get_active()

        config_changed = False
        if (pkg.getMetaData(NS, 'export-dir') != d):
            pkg.setMetaData(NS, 'export-dir', d)
            pkg._modified = True
        if (config.data.preferences.get('visuallearning-vie-path') != vie):
            config.data.preferences['visuallearning-vie-path'] = vie
            config_changed = True
        if (config.data.preferences.get('visuallearning-template-path') != template):
            config.data.preferences['visuallearning-template-path'] = template
            config_changed = True
        if config_changed:
            config.data.save_preferences()

        b.set_sensitive(False)
        self.convert_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.should_continue = True

        try:
            export(pkg,
                   self.controller,
                   destination=d,
                   vie=vie,
                   template=template,
                   exprender=exprender,
                   browse=browse,
                   progress_callback=self.report_progress,
            )
            self.controller.log(_("VisualLearning export to %s completed") % d)
        except AbortExport:
            self.controller.log(_("VisualLearning export aborted"))
        except Exception, e:
            dialog.message_dialog(_("Could not export data: ") + unicode(e),
                                  icon=gtk.MESSAGE_ERROR)
            report_progress(0,"")
            import traceback; self.controller.log(traceback.format_exc())
        finally:
            self.should_continue = False
            b.set_sensitive(True)
            self.convert_button.set_sensitive(True)
            self.cancel_button.set_sensitive(False)
        return True

    def do_cancel(*p):
        if self.should_continue:
            self.should_continue = False
        return True

        
    def build_widget(self):        
        pkg = self.controller.package
                
        v=gtk.VBox()


        ## expressive rendering
        hb=gtk.HBox()
        toggle=gtk.CheckButton(_("Use Expressive Rendering"))
        toggle.set_active(self.compute_exprender())
        toggle.show()
        toggle.connect('clicked', self.toggle_exprender)
        hb.add(toggle)
        v.pack_start(hb, expand=False)

        hb=gtk.HBox()
        self.exprender_toggle = toggle
        b=gtk.Button(stock=gtk.STOCK_CONVERT)
        b.connect('clicked', self.do_convert)
        hb.pack_start(b, expand=False)
        self.convert_button = b
        v.pack_start(hb, expand=False)

        ## web export
        hb=gtk.HBox()
        hb.pack_start(gtk.Label(_("Output dir")), expand=False)
        entry=gtk.Entry()
        entry.set_text(pkg.getMetaData(NS, 'export-dir') or "")
        hb.add(entry)
        self.dirname_entry = entry
        b=gtk.Button(stock=gtk.STOCK_OPEN)
        def select_dir(*p):
            d=dialog.get_dirname(_("Specify the output directory"),
                                 default_dir=self.dirname_entry.get_text(),
            )
            if d is not None:
                self.controller.log("Setting VL output dir to %s" % d)
                self.dirname_entry.set_text(d)
            return True
        b.connect('clicked', select_dir)
        hb.pack_start(b, expand=False)
        v.pack_start(hb, expand=False)

        hb=gtk.HBox()
        toggle=gtk.CheckButton(_("Open in browser"))
        toggle.set_active(True)
        toggle.show()
        hb.pack_start(toggle, expand=False)
        self.browse_toggle = toggle
        v.pack_start(hb, expand=False)

        hb=gtk.HButtonBox()
        b=gtk.Button(_("Export"))
        b.connect('clicked', self.do_export)
        hb.add(b)
        self.export_button = b
        b=gtk.Button(stock=gtk.STOCK_CANCEL)
        b.connect('clicked', self.do_cancel)
        b.set_sensitive(False)
        hb.add(b)
        self.cancel_button = b
        v.pack_start(hb, expand=False)


        ## progress bar
        self.progress_bar = gtk.ProgressBar()
        v.pack_start(self.progress_bar, expand=False)


        ## advanced option

        sep = gtk.HSeparator()
        v.pack_start(sep)

        hb=gtk.HBox()
        hb.pack_start(gtk.Label(_("VIE path")), expand=False)
        entry=gtk.Entry()
        entry.set_tooltip_text(_("Path of the Expressive Rendering utility"))
        entry.set_text(config.data.preferences.get('visuallearning-vie-path') or "")
        hb.add(entry)
        self.vie_entry = entry

        b=gtk.Button(stock=gtk.STOCK_OPEN)
        def select_vie(*p):
            path=dialog.get_filename(
                _("Specify the path of the Expressive Rendering utility"),
                default_file=self.vie_entry.get_text(),
            )
            if path is not None:
                self.controller.log("Setting VIE path to %s" % path)
                self.vie_entry.set_text(path)
            return True
        b.connect('clicked', select_vie)
        hb.pack_start(b, expand=False)
        v.pack_start(hb, expand=False)


        hb=gtk.HBox()
        hb.pack_start(gtk.Label(_("Template path")), expand=False)
        entry=gtk.Entry()
        entry.set_tooltip_text(
            _("Path of the template directory (leave blank to use default template)"))
        entry.set_text(config.data.preferences.get('visuallearning-template-path') or "")
        hb.add(entry)
        self.template_entry = entry

        b=gtk.Button(stock=gtk.STOCK_OPEN)
        def select_template(*p):
            d=dialog.get_dirname(_("Specify the template directory"),
                                 default_dir=self.template_entry.get_text(),
            )
            if d is not None:
                self.controller.log("Setting VL template dir to %s" % d)
                self.template_entry.set_text(d)
            return True
        b.connect('clicked', select_template)
        hb.pack_start(b, expand=False)
        v.pack_start(hb, expand=False)


        return v


def export(package, controller, destination='/tmp/n', vie=None, template=None, exprender=True, browse=True, progress_callback=None):
                
    if progress_callback is None:
        progress_callback = lambda a,b: None
           
    progress_callback(0, "checking destination dir")
    if os.path.exists(destination) and not os.path.isdir(destination):
        controller.log(_("%s exists but is not a directory. "
                         "Cancelling visuallearning export") % destination)
        return
    if not os.path.exists(destination):
        # we perform recursive_mkdir *even* if template is not None,
        # (and hence we have to delete the corresponding dir afterwards)
        # because we may have to create *parent* directories
        helper.recursive_mkdir(destination)
        if not os.path.isdir(destination):
            controller.log(_("could not create directory %s") % destination)
            return
    if template:
        shutil.rmtree(destination)


    html_filename = os.path.join(destination, "index.html")

    if template:
        progress_callback(.1, "copying template")
        shutil.rmtree(destination, True)
        shutil.copytree(template, destination)
        f = open(html_filename)
        try:
            html_content = f.read().decode("utf-8")
        finally:
            f.close()
    else:
        progress_callback(.1, "copying default template")
        f = open(os.path.join(destination, "jquery.js"), "w")
        try:
            f.write(CONTENTS["jquery.js"]);
        finally:
            f.close()
        f = open(os.path.join(destination, "popcorn-complete.js"), "w")
        try:
            f.write(CONTENTS["popcorn-complete.js"]);
        finally:
            f.close()
        f = open(os.path.join(destination, "visual-learning.js"), "w")
        try:
            f.write(CONTENTS["visual-learning.js"]);
        finally:
            f.close()
        html_content = CONTENTS["index.html"]
    

    progress_callback(.2, "generating JSON structure")
    annotations = {}
    media_duration = package.getMetaData(
        "http://experience.univ-lyon1.fr/advene/ns/advenetool", "duration")
    if media_duration is not None:
        annotations["media_duration"] = int(media_duration)/1000
    skips = []
    for a in package.get_element_by_id("coupe").annotations:
        skips.append({
                "start": a.fragment.begin / 1000,
                "end": a.fragment.end / 1000,
                })
    annotations["skips"] = skips        
    subtitles = []
    for a in package.get_element_by_id("soustitre").annotations:
        subtitles.append({
                "start": a.fragment.begin / 1000,
                "end": a.fragment.end / 1000,
                "text": a.contentData,
                })
    annotations["subtitles"] = subtitles
    pauses = []
    for a in package.get_element_by_id("pause").annotations:
        data = a.content.parsed()
        if "texte" in data:
            text = data["texte"]
            if "url" in data:
                text = '<a href="%s">%s</a>' % (data["url"], text)
        else:
            text = data["_all"]
        pauses.append({
                "time": a.fragment.begin / 1000,
                "text": text,
                })
    annotations["pauses"] = pauses
    svgs = []
    svg_annotations = package.get_element_by_id("surtitre").annotations
    if not exprender:
        interpolation_module = controller.gui.registered_adhoc_views.get('svg_interpolation')
        v = interpolation_module(controller)
        v.generate(controller.package.get_element_by_id('rendu_expressif'),
                   controller.package.get_element_by_id('interpolation'),
                   )
        svg_annotations = itertools.chain(
            svg_annotations,
            package.get_element_by_id("interpolation").annotations,
            )
    for a in svg_annotations:
        text = a.contentData
        # remove svg namespace, as it is unrecognized in HTML5
        text = text.replace("<svg:", "<").replace("</svg:", "</")
        # remove width and height specifications in top-level SVG tag
        text = re.subn(r' +width="[^"]*"', "", text, 1)[0]
        text = re.subn(r' +height="[^"]*"', "", text, 1)[0]
        svgs.append({
                "start": a.fragment.begin / 1000,
                "end": a.fragment.end / 1000,
                "text": text,
                })
    annotations["svgs"] = svgs
    annotations_json = json.dumps(annotations, indent=4)


    progress_callback(.5, "generating index.html")
    video_src = controller.get_default_media(package)
    video_name = os.path.split(video_src)[-1]
    html_content = html_content.replace('src="the-video-file"',
                                        'src="%s"' % video_name
                                        )
    html_content = html_content.replace("the-title-of-the-page",
                                        package.getTitle())
    html_content = html_content.replace("the-author-of-the-page",
                                        package.getAuthor())
    html_content = html_content.replace("the-visual-learning-data",
                                        annotations_json)
    f = open(html_filename, "w")
    try:
        f.write(html_content)
    finally:
        f.close()

    video_dest = os.path.join(destination, video_name)
    progress_callback(.6, "copying video")
    shutil.copy(video_src, video_dest)

    if browse:
        progress_callback(.9, "opening index.html in browser")
        controller.open_url(html_filename)

    progress_callback(1, "done")




class AbortExport(Exception):
    pass

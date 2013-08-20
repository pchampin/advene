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
import mimetypes
import os
import re
import shutil

import advene.core.config as config
import advene.util.helper as helper

from advene.gui.util import dialog


NS = "http://omendo.fr/visuallearning/"
name = "Visual Learning exporter"

def register(controller):
    pass # TODO make this a proprer plugin


def display_gui(controller):
    
    pkg = controller.package
    
    w=gtk.Window()
    
    v=gtk.VBox()
    w.set_title(_("VisualLearning export"))
    v.add(gtk.Label(_("Exporting views to a VisualLearning page")))

    hb=gtk.HBox()
    hb.pack_start(gtk.Label(_("Output directory")), expand=False)
    dirname_entry=gtk.Entry()
    d=pkg.getMetaData(NS, 'export-directory')
    if d is not None:
        dirname_entry.set_text(d)
    hb.add(dirname_entry)

    d=gtk.Button(stock=gtk.STOCK_OPEN)
    def select_dir(*p):
        d=dialog.get_dirname(_("Specify the output directory"))
        if d is not None:
            dirname_entry.set_text(d)
        return True
    d.connect('clicked', select_dir)
    hb.pack_start(d, expand=False)
    v.pack_start(hb, expand=False)

    hb=gtk.HBox()
    hb.pack_start(gtk.Label(_("JQuery URL")), expand=False)
    jquery_entry=gtk.Entry()
    jquery_entry.set_tooltip_text(_("URL of the JQuery library (leave blank to generate local copy)"))
    jquery_entry.set_text(pkg.getMetaData(NS, 'export-jquery-filename') or "")
    hb.add(jquery_entry)
    v.pack_start(hb, expand=False)

    hb=gtk.HBox()
    hb.pack_start(gtk.Label(_("Popcorn URL")), expand=False)
    popcorn_entry=gtk.Entry()
    popcorn_entry.set_tooltip_text(_("URL of the Popcorn library (leave blank to generate local copy)"))
    popcorn_entry.set_text(pkg.getMetaData(NS, 'export-popcorn-filename') or "")
    hb.add(popcorn_entry)
    v.pack_start(hb, expand=False)

    hb=gtk.HBox()
    exprender_toggle=gtk.CheckButton(_("Expressive rendering"))
    exprender_toggle.set_active(True)
    exprender_toggle.show()
    hb.pack_start(exprender_toggle, expand=False)
    v.pack_start(hb, expand=False)

    hb=gtk.HBox()
    browse_toggle=gtk.CheckButton(_("Open in browser"))
    browse_toggle.set_active(True)
    browse_toggle.show()
    hb.pack_start(browse_toggle, expand=False)
    v.pack_start(hb, expand=False)

    pb=gtk.ProgressBar()
    v.pack_start(pb, expand=False)

    w.should_continue = False

    def cb(val, msg):
        if not w.should_continue:
            raise AbortExport()
        if val >= 0 and val <= 1.0:
            pb.set_fraction(val)
        if len(msg) > 80:
            msg = msg[:36] + "(...)" + msg[-36:]
        pb.set_text(msg)
        while gtk.events_pending():
            gtk.main_iteration()

    def do_conversion(b):
        d=unicode(dirname_entry.get_text())
        if not d:
            dialog.message_dialog(_("No destination directory provided"), icon=gtk.MESSAGE_ERROR)
            return False

        jquery=jquery_entry.get_text() or None
        popcorn=popcorn_entry.get_text() or None
        exprender = exprender_toggle.get_active()
        browse = browse_toggle.get_active()

        if (pkg.getMetaData(NS, 'export-directory') != d
            or pkg.getMetaData(NS, 'export-jquery-url') != jquery
            or pkg.getMetaData(NS, 'export-popcorn-url') != popcorn):
            pkg._modified = True
        pkg.setMetaData(NS, 'export-directory', d)
        pkg.setMetaData(NS, 'export-jquery-filename', jquery or None) # unset if empty
        pkg.setMetaData(NS, 'export-popcorn-filename', popcorn or None) # unset if empty

        b.set_sensitive(False)
        w.should_continue = True

        try:
            export(pkg,
                   controller,
                   destination=d,
                   jquery=jquery,
                   popcorn=popcorn,
                   exprender=exprender,
                   browse=browse,
                   progress_callback=cb)
            controller.log(_("VisualLearning export to %s completed") % d)
        except AbortExport:
            controller.log(_("VisualLearning export aborted"))
            w.destroy()
        except Exception, e:
            dialog.message_dialog(_("Could not export data: ") + unicode(e), icon=gtk.MESSAGE_ERROR)
            cb(0,"")
            import traceback; traceback.print_exc()
        w.should_continue = False
        b.set_sensitive(True)
        return True

    dirname_entry.connect('activate', do_conversion)

    def do_cancel(*p):
        if w.should_continue:
            w.should_continue = False
        else:
            w.destroy()
        return True

    hb=gtk.HButtonBox()
    b=gtk.Button(stock=gtk.STOCK_CONVERT)
    b.connect('clicked', do_conversion)
    hb.add(b)
    b=gtk.Button(stock=gtk.STOCK_CLOSE)
    b.connect('clicked', do_cancel)
    hb.add(b)
    v.pack_start(hb, expand=False)

    w.add(v)

    w.show_all()
    return True


def export(package, controller, destination='/tmp/n', jquery=None, popcorn=None, exprender=True, browse=True, progress_callback=None):
                
    if progress_callback is None:
        progress_callback = lambda a,b: None
           
    progress_callback(0, "checking destination dir")
    if not os.path.exists(destination):
        helper.recursive_mkdir(destination)
        if not os.path.isdir(destination):
            controller.log(_("could not create directory %s") % destination)
            return
    elif os.path.exists(destination) and not os.path.isdir(destination):
        controller.log(_("%s exists but is not a directory. Cancelling visuallearning export") % destination)
        return


    progress_callback(.1, "retrieving HTML template")
    plugin_dir = os.path.dirname(__file__)
    html_filename = os.path.join(plugin_dir, "page.html")
    f = open(html_filename)
    try:
        html_content = f.read()
    finally:
        f.close()

    if jquery:
        html_content = html_content.replace('src="jquery.js"',
                                            'src="%s"' % jquery)
    else:
        progress_callback(.2, "copying jquery.js")
        shutil.copy(os.path.join(plugin_dir, "jquery.js"),
                    os.path.join(destination, "jquery.js"))

    if popcorn:
        html_content = html_content.replace('src="popcorn-complete.js"',
                                            'src="%s"' % popcorn)
    else:
        progress_callback(.3, "copying popcorn-complete.js")
        shutil.copy(os.path.join(plugin_dir, "popcorn-complete.js"),
                    os.path.join(destination, "popcorn-complete.js"))

    
    progress_callback(.4, "generating index.html")
    video_src = controller.get_default_media(package)
    video_name = os.path.split(video_src)[-1]
    html_content = html_content.replace('src="video.webm"',
                                        'src="%s"' % video_name
                                        )
    html_content = html_content.replace("the-title-of-the-page",
                                        package.getTitle())
    html_content = html_content.replace("the-author-of-the-page",
                                        package.getAuthor())
    html_filename = os.path.join(destination, "index.html")
    f = open(html_filename, "w")
    try:
        f.write(html_content)
    finally:
        f.close()

    progress_callback(.5, "generating JSON structure")
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
        svg_annotations = itertools.chain(
            svg_annotations,
            package.get_element_by_id("rendu_expressif").annotations,
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

    progress_callback(.6, "generating visual-learning.js")
    js_src = os.path.join(plugin_dir, "visual-learning.js")
    f = open(js_src)
    try:
        js_content = f.read()
    finally:
        f.close()
    js_content = js_content.replace("= TEST_DATA;",
                                    "= %s;" % annotations_json)
    js_filename = os.path.join(destination, "visual-learning.js")
    f = open(js_filename, "w")
    try:
        f.write(js_content)
    finally: 
        f.close()
    progress_callback(.7, "visual-learning.js generated")


    video_dest = os.path.join(destination, video_name)
    if exprender:
        progress_callback(.8, "rendering video")
        # TODO invoke expressive rendering generator instead
        shutil.copy(video_src, video_dest)
    else:
        progress_callback(.8, "copying video")
        shutil.copy(video_src, video_dest)

    if browse:
        progress_callback(.9, "opening index.html in browser")
        controller.open_url(html_filename)

    progress_callback(1, "done")




class AbortExport(Exception):
    pass

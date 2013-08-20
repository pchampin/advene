$(document).on("DOMContentLoaded", function() {

    var screen = $("#screen")[0];
    var video = Popcorn("#video");
    var pausepanel = $("#pausepanel")[0];

    /********************************
     * set up player
     */
    var playpause = $("#playpause")[0];
    var timebar = $("#timebar")[0];
    var timelabel = $("#timelabel")[0];

    video.on("play", function() {
            pausepanel.style.display = "none";
            playpause.innerHTML = "||";
            video.enable("code");
    });

    video.on("pause", function() {
            playpause.innerHTML = "&gt;";
            video.disable("code");
    });

    function toggle_playpause() {
        if (video.paused()) {
            video.play();
        } else {
            video.pause();
        }
    }

    /** play-pause is toggled by 1) button, 2) click on video, 3) space bar */

    $(playpause).on("click", toggle_playpause);
    $("#screen").on("click", toggle_playpause);
    $("body").on("keypress", function(event) {
        if (event.which === 32 && // space bar
            event.target.tagName !== "BUTTON" // do not overload 'click'
           ) {
            console.log(event.target);
            toggle_playpause();
        }
    });

    /** forward and backward
        NB: navigating with those buttons (and the timebar, see below)
        disables the pause panel,
        and temporily disables the 'skip' annotations,
        in order to make navigation more intuitive.
        */

    var navigation_timeout;
    
    function set_navigation_mode() {
        video.disable("code");
        pausepanel.style.display = "none";
        clearTimeout(navigation_timeout);
        navigation_timeout = setTimeout(function() {
            if (!video.paused()) {
                video.enable("code");
            }
        }, 500);
    }


    $("#rewind").on("click", function() {
        set_navigation_mode();
        video.currentTime(video.currentTime() - 5);
    });

    $("#forward").on("click", function() {
        set_navigation_mode();
        video.currentTime(video.currentTime() + 5);
    });


    /** #timebar is synchronized both ways with currentTime. */

    var timebar_timeout;
    $(timebar).on("change", function() {
        set_navigation_mode();
        video.currentTime(timebar.value);
    });

    video.on("timeupdate", function(event) {
        timebar.value = video.currentTime();
        sec = video.roundTime();
        min = Math.floor(sec / 60);
        sec = sec % 60;
        if (sec < 10) { sec = "0" + sec; }
        timelabel.innerHTML = min + ":" + sec;
    });

    video.on("loadedmetadata", function() {
        screen.style.height = video.position().height + "px";
        if (video.seekable().length === 0) {
            // apparently, video is not seekable
            timebar.disabled = true;
            $("#rewind")[0].disabled = true;
            $("#forward")[0].disabled = true;
        }
        if (annotations.media_duration) {
            timebar.max = annotations.media_duration;
        } else {
            timebar.max = video.media.duration;
            /* some browsers (e.g. FF) fail to load it over HTTP,
               hence the possibility to provided it with the data. */
        }

        populate_annotations();
        video.play();
    });
     

    /********************************
     * set up annotations
     */

    var subtitles = $("#subitles")[0];
    var svg = $("#svg")[0];

    function populate_annotations() {
        /* useful stuff for handling annotations */
        var wsvg = video.position().width;
        var hsvg = video.position().height;
        var redcross = ('<svg viewBox="0 0 '+ wsvg + ' ' + hsvg + '" '+
                        ' style="stroke: red; stroke-width: 4px">'+
                        '<line x1="0" y1="0" x2="100%" y2="100%"/>'+
                        '<line x1="100%" y1="0" x2="0" y2="100%"/>'+
                        '</svg>'
                       );

        var skip_security = 1;

        function skipper(a) {
            video.play(a.end + skip_security);
        }
        function pauser(a) {
            pausepanel.innerHTML = a.text;
            pausepanel.style.display = "block";
            video.pause();
        }

        /* passing annotations to popcorn */
        var i, a;
        for(i=0; i< annotations.skips.length; i+=1) {
            a = annotations.skips[i];
            video.code({
                start: a.start,
                end: a.end-skip_security,
                onFrame: skipper,
            });
            video.subtitle({ // visually mark those parts as being skipped
                start: a.start,
                end: a.end,
                text: redcross,
                target: "svg",
            });
            i += 1;
        }
        for(i=0; i< annotations.subtitles.length; i+=1) {
            a = annotations.subtitles[i];
            a.target = "subtitles";
            video.subtitle(a);
        }
        for(i=0; i< annotations.svgs.length; i+=1) {
            a = annotations.svgs[i];
            a.target = "svg";
            video.subtitle(a);
        }
        for(i=0; i< annotations.pauses.length; i+=1) {
            a = annotations.pauses[i];
            video.code({
                start: a.time-1,
                end: a.time,
                text: a.text,
                onEnd: pauser,
            });
        }

        console.log("visual-learning annotations loaded");
    }

    var TEST_DATA = {
        "media_duration": 1010.81,
        "skips": [
            {
                start: 0,
                end: 19
            }
        ],
        "subtitles": [
            {
                start: 20,
                end: 22,
                text: "This is a subtitle",
            },
        ],
        "svgs": [
            {
                start: 21,
                end: 24,
                text: '<svg viewBox="0 0 640 355"><text fill="red" name="Texte" stroke="red" style="stroke-width:1; font-family: sans-serif; font-size: 20" x="180" y="62">This is SVG</text><ellipse cx="357" cy="73" fill="none" name="Forme générique" rx="43" ry="55" stroke="red" style="stroke-width:2" /><line x1="0", y1="50%" x2="100%" y2="50%" stroke="yellow"/></svg>',
            },
        ],
        "pauses": [
            {
                time: 23,
                text: "This is a pause",
            },
        ],
    };

    var annotations = TEST_DATA;

    console.log("visual-learning script loaded");
});

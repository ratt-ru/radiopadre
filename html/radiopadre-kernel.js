//
// socket.io needs to be invoked here like this -- not that I understand the full syntax.
// Calling it from a cell's output causes Jupyter to do something fatal to the socket connection. Probably
// for security reasons, same motivation why a cell's output can't invoke Javascript from other sites.
// So, we instantiate it here.
//


define(['base/js/namespace', 'base/js/promises', 'socket.io' ], function(Jupyter, promises, io1) {

promises.app_initialized.then(function(appname) {
if (appname === 'NotebookApp')
{
    io = io1

    console.log("initializing radiopadre components")

//    var width = $(".rendered_html")[0].clientWidth;
//
//    console.log("reset display, width is", window.innerWidth, window.innerHeight);

//    Jupyter.notebook.kernel.execute(`import radiopadre; radiopadre.set_window_sizes(
//                                            ${width},
//                                            ${window.innerWidth}, ${window.innerHeight})`);


    document.radiopadre = {}

//    document.radiopadre.fixup_hrefs = function ()
//    {
//        $("a[href*='/#NOTEBOOK_FILES#/']").each(function() {
//                this.href = this.href.replace("/#NOTEBOOK_FILES#/","/files/"+document.radiopadre.notebook_dir);
//           });
//        $("a[href*='/#NOTEBOOK_NOTEBOOKS#/']").each(function() {
//                this.href = this.href.replace("/#NOTEBOOK_NOTEBOOKS#/","/notebooks/"+document.radiopadre.notebook_dir);
//           });
//        $("img[src*='/#NOTEBOOK_FILES#/']").each(function() {
//                this.src = this.src.replace("/#NOTEBOOK_FILES#/","/files/"+document.radiopadre.notebook_dir);
//           });
//    }

    document.radiopadre.execute_to_current_cell = function ()
    {
        var current =  Jupyter.notebook.get_selected_index();
        Jupyter.notebook.execute_cell_range(0,current+1);
    }

    document.radiopadre.handle_copy_notebook_output = function (out)
    {
        console.log('copy_current_notebook output ' + JSON.stringify(out));
        if( out.header.msg_type == 'error' ) {
            var ename = out.content.ename;
            var evalue = out.content.evalue;
            console.log('error: '+ename+', '+evalue)
            IPython.dialog.modal({
                title: "Error copying notebook",
                body: "There was an error copying the notebook: "+ename+", "+evalue,
                buttons: { OK : { class : "btn-primary" } }
            });
        } else if( out.header.msg_type == 'execute_result' ) {
            var path = out.content.data['text/plain']
            path = path.replace(/^['"](.*)['"]$/, '$1')
            console.log('success: '+path);
            Jupyter.notebook.execute_cell();
            window.open('/notebooks/'+path,'_blank')
        }
    }

    document.radiopadre.copy_notebook = function (path, copy_dirs, copy_root)
    {
        var kernel = Jupyter.notebook.kernel;
        var callbacks = {'iopub': {'output' : document.radiopadre.handle_copy_notebook_output}};
        var index = Jupyter.notebook.get_selected_index();
        var command = 'radiopadre.copy_current_notebook('
            +'"'+Jupyter.notebook.notebook_path+'","'+path+'",'
            +'cell='+index.toString()+','
            +'copy_dirs="'+copy_dirs+'",'
            +'copy_root="'+copy_root+'"'
            +');'
        console.log('running '+command)
        kernel.execute('import radiopadre')
        kernel.execute(command, callbacks, {silent:false});
    }
    document.radiopadre.protect = function (author)
    {
        Jupyter.notebook.metadata.radiopadre_notebook_protect = 1;
        Jupyter.notebook.metadata.radiopadre_notebook_scrub = 1;
        Jupyter.notebook.metadata.radiopadre_notebook_author = author;
        document.radiopadre.controls.update();
    }

    document.radiopadre.unprotect = function ()
    {
        Jupyter.notebook.metadata.radiopadre_notebook_protect = 0;
        document.radiopadre.controls.update();
    }

    document.radiopadre.controls = {}

    document.radiopadre.controls.update = function ()
    {
        var prot = document.radiopadre.controls.button_protected;
        var scrub = document.radiopadre.controls.button_scrub;
        scrub.disabled = false;
        var save = IPython.menubar.element.find("#save_checkpoint");
        save.enable = true;
//        if( Jupyter.notebook.metadata.radiopadre_notebook_protect ) {
//            Jupyter.notebook.set_autosave_interval(0);
//            prot.visibility = 'visible'
//            var author = Jupyter.notebook.metadata.radiopadre_notebook_author;
//            if( author == document.radiopadre.user ) {
//                prot.innerHTML = 'author';
//                prot.title  = 'This is a protected radiopadre notebook, but you are the author. ';
//                prot.title += 'You may modify and save the notebook, but auto-save is disabled. ';
//                prot.title += 'Use radiopadre.unprotect() to unprotect this notebook.';
//            } else {
//                prot.innerHTML = 'protected';
//                prot.title = 'This radiopadre notebook is protected by author "' + author + '".';
//                prot.title += 'You may modify, but you cannot save the notebook. ';
//                prot.title += 'Use radiopadre.unprotect() to unprotect this notebook.';
//                scrub.disabled = true;
//                Jupyter.notebook.metadata.radiopadre_notebook_scrub = true;
//                save.enable = false;
//            }
//        } else {
//            prot.innerHTML = 'unprotected';
//            prot.visibility = 'hidden';
//            prot.title = 'This is an unprotected radiopadre notebook, it may be modified and saved at will. ';
//            prot.title += 'Use radiopadre.protect([author]) to protect this notebook.';
//        }
        if( Jupyter.notebook.metadata.radiopadre_notebook_scrub ) {
            scrub.innerHTML = 'scrub: on';
            scrub.title = 'Scrubbing is on: will scrub all cell output when saving this notebook. Click to toggle.';
        } else {
            scrub.innerHTML = 'scrub: off';
            scrub.title = 'Scrubbing off: will retain cell output when saving this notebook. Click to toggle.';
        }
        var width_btn = document.radiopadre.controls.button_width;
        if( document.radiopadre._full_width ) {
            width_btn.innerHTML = '&rarr;default width&larr;';
            width_btn.title = 'Reset notebook display to default width.';
        } else {
            width_btn.innerHTML = '&larr;<nbsp>full width<nbsp>&rarr;';
            width_btn.title = 'Set notebook display to full browser width.';
        }
    }

    document.radiopadre.toggle_scrubbing = function()
    {
        Jupyter.notebook.metadata.radiopadre_notebook_scrub = !Jupyter.notebook.metadata.radiopadre_notebook_scrub;
        document.radiopadre.controls.update();
    }

    document.radiopadre._full_width = 0
    document.radiopadre.toggle_width = function()
    {
        document.radiopadre.controls.update();
        document.radiopadre._full_width = !document.radiopadre._full_width;
        container = document.getElementById("notebook-container");
//        console.log("container is", container, 'offsetWidth:', container.offsetWidth, 'style.width:', container.style.width, ';')
        if( document.radiopadre._full_width ) {
            document.radiopadre._default_width_px = container.style.width;
            container.style.width = "100%";
//            console.log("set 100% width");
        } else {
            container.style.width = document.radiopadre._default_width_px;
//            console.log("set default width", document.radiopadre._default_width_px);
        }
        document.radiopadre.controls.update();
    }


    document.radiopadre.before_unload = function (e) {
        console.log("before unload")
        if( Jupyter.notebook.metadata.radiopadre_notebook_protect &&
            Jupyter.notebook.metadata.radiopadre_notebook_author != document.radiopadre.user)
        {
            Jupyter.notebook.set_dirty(false);
        }
        return document.radiopadre._old_beforeunload(e);
    }

    document.radiopadre.init_controls = function (user)
    {
        // run only once
        if( document.radiopadre.user )
            return;
        // // causes TypeError since the notebook is marked as non-extensible
        // Jupyter.notebook._save_notebook_orig = Jupyter.notebook.save_notebook
        document.radiopadre.user = user;
        if( document.getElementById("radiopadre_controls") == null ) {
            console.log("initializing radiopadre controls");
            var label = $('<span/>').addClass("navbar-text").text('Radiopadre:');
            IPython.toolbar.element.append(label);
            IPython.toolbar.add_buttons_group([
                {   'id'      : 'radiopadre_btn_exec_all',
                    'label'   : 'Click to rerun all cells in this radiopadre notebook.',
                    'icon'    : 'icon-arrow-up',
                    'callback': function () { Jupyter.notebook.execute_all_cells() }
                },
                {   'id'      : 'radiopadre_btn_scrub',
                    'label'   : 'Scrubs output from all cells in the notebook',
                    'icon'    : 'icon-stop',
                    'callback': function () { document.radiopadre.toggle_scrubbing() }
                },
//                {   'id'      : 'radiopadre_btn_protected',
//                    'label'   : 'This notebook is protected',
//                    'icon'    : 'icon-play-circle',
//                    'callback':  function () { Jupyter.notebook.execute_cell() }
//                },
                {   'id'      : 'radiopadre_btn_width',
                    'label'   : 'width',
                    'icon'    : 'icon-play-circle',
                    'callback':  function () { document.radiopadre.toggle_width() }
                }
                ],'radiopadre_controls');
            var save = IPython.menubar.element.find("#save_checkpoint");
            save.enable = true;
        }
        document.getElementById("radiopadre_btn_exec_all").innerHTML = "Run all";
        document.radiopadre.controls.button_scrub = document.getElementById("radiopadre_btn_scrub")
        document.radiopadre.controls.button_protected = document.getElementById("radiopadre_btn_protected")
        document.radiopadre.controls.button_width = document.getElementById("radiopadre_btn_width")
        document.radiopadre.controls.update();
        var nbpath = Jupyter.notebook.notebook_path;
        if( nbpath.search('/') >=0 ) {
            var nbdir = nbpath.replace(/\/[^\/]*$/, '/');
        } else {
            var nbdir = ''
        }
        console.log("notebook directory relative to server is "+nbdir);
        document.radiopadre.notebook_dir = nbdir;

        // mark protected notebooks as non-dirty so that it doesn't caomplain about not saving
        if( !document.radiopadre._old_beforeunload ) {
            document.radiopadre._old_beforeunload = window.onbeforeunload
            window.onbeforeunload = document.radiopadre.before_unload
        }
    }

    document.radiopadre.register_user = function (user)
    {
        document.radiopadre.user = user;
        document.radiopadre.controls.update();
    }

    // init controls for null user
    document.radiopadre.init_controls('')


    // sequence of scripts need to be loaded for JS9
    // this is a global variable -- it can be appended to in the cell-side JS9 init code
    // (with e.g. a custom js9partners.js script, since at this point we don't have its location)
    js9_script_sequence = [
                           '/static/js9-www/js9prefs.js',
                           '/files/.radiopadre-session/js9prefs.js',
                           '/static/js9-www/js9support.min.js',
                           '/static/js9-www/js9.min.js',
                           '/static/js9-www/js9plugins.js',
                           '/static/js9-www/js9colormaps.js',
                           '/static/radiopadre-www/js9partners.js'
                          ]

    js9init_script_sequencer = function () {
        if( js9_script_sequence.length ) {
            script = js9_script_sequence.shift()
            console.log('loading', script)
            s = document.createElement("script");
            s.src = script;
            s.onload = js9init_script_sequencer;
            js9init_element.appendChild(s);
        } else {
          console.log('all JS9 components loaded');
        }
    }

    var js9init_element = document.createElement("div");
    js9init_element.innerHTML = "\
      <link type='image/x-icon' rel='shortcut icon' href='/static/js9-www/favicon.ico'>\
      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9support.css'>\
      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9.css'>\
      <link rel='apple-touch-icon' href='/static/js9-www/images/js9-apple-touch-icon.png'>\
      <script type='text/javascript'> js9init_script_sequencer(); </script>\
    "
    Jupyter.toolbar.element.append(js9init_element);

//    var js9init_element = document.createElement("div");
//
//    js9init_element.innerHTML = "\
//      <link type='image/x-icon' rel='shortcut icon' href='/static/js9-www/favicon.ico'>
//      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9support.css'>\
//      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9.css'>\
//      <link rel='apple-touch-icon' href='/static/js9-www/images/js9-apple-touch-icon.png'>\
//      <script type='text/javascript'> js9init_script_sequencer(); </script>\
//    ";
//    Jupyter.toolbar.element.append(js9init_element);

//    // load JS9 components
//    var wrapper = document.createElement("div");
//    wrapper.innerHTML = "\
//      <link type='image/x-icon' rel='shortcut icon' href='/static/js9-www/favicon.ico'>\
//      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9support.css'>\
//      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9.css'>\
//      <link rel='apple-touch-icon' href='/static/js9-www/images/js9-apple-touch-icon.png'>\
//      <script type='text/javascript' src='/static/js9-www/js9prefs.js'></script>\
//      <script type='text/javascript'> console.log('loaded JS9 prefs 1') </script>\
//      <script type='text/javascript' src='/files/.radiopadre-session/js9prefs.js'></script>\
//      <script type='text/javascript'> console.log('loaded JS9 prefs 2')</script>\
//      <script type='text/javascript' src='/static/js9-www/js9support.min.js'></script>\
//      <script type='text/javascript' src='/static/js9-www/js9.min.js'></script>\
//      <script type='text/javascript' src='/static/js9-www/js9plugins.js'></script>\
//      <script type='text/javascript'> console.log('loaded JS9 components') </script>\
//      <script type='text/javascript' src='/static/radiopadre-www/js9partners.js'></script>\
//      <script type='text/javascript'> console.log('loaded JS9 partner plugin') </script>\
//      <script type='text/javascript' src='/static/js9colormaps.js'></script>\
//    "
//    Jupyter.toolbar.element.append(wrapper);



}
})

return function () {};
})
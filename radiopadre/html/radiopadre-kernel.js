define([
        'base/js/namespace',
        'base/js/promises'
     ], function(Jupyter, promises) {
         promises.app_initialized.then(function(appname) {
             if (appname === 'NotebookApp') {
                 load_radiopadre()
             }
         });

//define(function(){
//  return {onload:onload}
//
//})
//
var load_radiopadre = function ()
{
    console.log("initializing radiopadre components")

    document.radiopadre = {}

    document.radiopadre.fixup_hrefs = function ()
    {
        $("a[href*='/#NOTEBOOK_FILES#/']").each(function() {
                this.href = this.href.replace("/#NOTEBOOK_FILES#/","/files/"+document.radiopadre.notebook_dir);
           });
        $("a[href*='/#NOTEBOOK_NOTEBOOKS#/']").each(function() {
                this.href = this.href.replace("/#NOTEBOOK_NOTEBOOKS#/","/notebooks/"+document.radiopadre.notebook_dir);
           });
        $("img[src*='/#NOTEBOOK_FILES#/']").each(function() {
                this.src = this.src.replace("/#NOTEBOOK_FILES#/","/files/"+document.radiopadre.notebook_dir);
           });
    }

    document.radiopadre.execute_to_current_cell = function ()
    {
        var current =  IPython.notebook.get_selected_index();
        IPython.notebook.execute_cell_range(0,current+1);
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
            IPython.notebook.execute_cell();
            window.open('/notebooks/'+path,'_blank')
        }
    }

    document.radiopadre.copy_notebook = function (path, copy_dirs, copy_root)
    {
        var kernel = IPython.notebook.kernel;
        var callbacks = {'iopub': {'output' : document.radiopadre.handle_copy_notebook_output}};
        var index = IPython.notebook.get_selected_index();
        var command = 'radiopadre.copy_current_notebook('
            +'"'+IPython.notebook.notebook_path+'","'+path+'",'
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
        IPython.notebook.metadata.radiopadre_notebook_protect = 1;
        IPython.notebook.metadata.radiopadre_notebook_scrub = 1;
        IPython.notebook.metadata.radiopadre_notebook_author = author;
        document.radiopadre.controls.update();
    }

    document.radiopadre.unprotect = function ()
    {
        IPython.notebook.metadata.radiopadre_notebook_protect = 0;
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
        if( IPython.notebook.metadata.radiopadre_notebook_protect ) {
            IPython.notebook.set_autosave_interval(0);
            prot.visibility = 'visible'
            var author = IPython.notebook.metadata.radiopadre_notebook_author;
            if( author == document.radiopadre.user ) {
                prot.innerHTML = 'author';
                prot.title  = 'This is a protected radiopadre notebook, but you are the author. ';
                prot.title += 'You may modify and save the notebook, but auto-save is disabled. ';
                prot.title += 'Use radiopadre.unprotect() to unprotect this notebook.';
            } else {
                prot.innerHTML = 'protected';
                prot.title = 'This radiopadre notebook is protected by author "' + author + '".';
                prot.title += 'You may modify, but you cannot save the notebook. ';
                prot.title += 'Use radiopadre.unprotect() to unprotect this notebook.';
                scrub.disabled = true;
                IPython.notebook.metadata.radiopadre_notebook_scrub = true;
                save.enable = false;
            }
        } else {
            prot.innerHTML = 'unprotected';
            prot.visibility = 'hidden';
            prot.title = 'This is an unprotected radiopadre notebook, it may be modified and saved at will. ';
            prot.title += 'Use radiopadre.protect([author]) to protect this notebook.';
        }
        if( IPython.notebook.metadata.radiopadre_notebook_scrub ) {
            scrub.innerHTML = 'scrub: on';
            scrub.title = 'Will scrub all cell output when saving this notebook. Click to toggle.';
        } else {
            scrub.innerHTML = 'scrub: off';
            scrub.title = 'Will retain cell output when saving this notebook. Click to toggle.';
        }
    }

    document.radiopadre.toggle_scrubbing = function()
    {
        IPython.notebook.metadata.radiopadre_notebook_scrub = !IPython.notebook.metadata.radiopadre_notebook_scrub;
        document.radiopadre.controls.update();
    }

    document.radiopadre.before_unload = function (e) {
        console.log("before unload")
        if( IPython.notebook.metadata.radiopadre_notebook_protect &&
            IPython.notebook.metadata.radiopadre_notebook_author != document.radiopadre.user)
        {
            IPython.notebook.set_dirty(false);
        }
        return document.radiopadre._old_beforeunload(e);
    }

    document.radiopadre.init_controls = function (user)
    {
        // run only once
        if( document.radiopadre.user )
            return;
        // // causes TypeError since the notebook is marked as non-extensible
        // IPython.notebook._save_notebook_orig = IPython.notebook.save_notebook
        document.radiopadre.user = user;
        if( document.getElementById("radiopadre_controls") == null ) {
            console.log("initializing radiopadre controls");
            var label = $('<span/>').addClass("navbar-text").text('Radiopadre:');
            IPython.toolbar.element.append(label);
            IPython.toolbar.add_buttons_group([
                {   'id'      : 'radiopadre_btn_exec_all',
                    'label'   : 'Click to rerun all cells in this radiopadre notebook.',
                    'icon'    : 'icon-arrow-up',
                    'callback': function () { IPython.notebook.execute_all_cells() }
                },
                {   'id'      : 'radiopadre_btn_scrub',
                    'label'   : 'Scrubs output from all cells in the notebook',
                    'icon'    : 'icon-stop',
                    'callback': function () { document.radiopadre.toggle_scrubbing() }
                },
                {   'id'      : 'radiopadre_btn_protected',
                    'label'   : 'This notebook is protected',
                    'icon'    : 'icon-play-circle',
                    'callback':  function () { IPython.notebook.execute_cell() }
                }
                ],'radiopadre_controls');
            var save = IPython.menubar.element.find("#save_checkpoint");
            save.enable = true;
        }
        document.getElementById("radiopadre_btn_exec_all").innerHTML = "Run all";
        document.radiopadre.controls.button_scrub = document.getElementById("radiopadre_btn_scrub")
        document.radiopadre.controls.button_protected = document.getElementById("radiopadre_btn_protected")
        document.radiopadre.controls.update();
        var nbpath = IPython.notebook.notebook_path;
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

    JS9p = {
        display_props: {},

        // checks if the given display has a colormap and scale saved -- resets if if so
        reset_scale_colormap: function(im)
        {
            props = JS9p.display_props[im.display.id];
            if( props ) {
              JS9.globalOpts.xeqPlugins = false;
              colormap = props.colormaps;
              scale = props.scale;
              console.log("saved scale and colormap",scale,colormap);
              if( colormap ) {
                  console.log("resetting colormap", colormap);
                  JS9.SetColormap(colormap.colormap, colormap.contrast, colormap.bias, {display: im});
              }
              if( scale ) {
                  console.log("resetting scale", scale);
                  JS9.SetScale(scale.scale, scale.smin, scale.smax, {display: im});
              }
              JS9.globalOpts.xeqPlugins = true;
            }
        },

        // registers two displays as partnered
        register_partners: function(d1, d2)
        {
            JS9p.display_props[d1] = {partner_display: d2}
            JS9p.display_props[d2] = {partner_display: d1}
        },

        // if display of image im has a partner, return it
        get_partner_display: function(im)
        {
            props = JS9p.display_props[im.display.id];
            return props ? props.partner_display : false;
        },

        // if display of image im has a partner, syncs colormap to it
        sync_partner_colormaps: function (im)
        {
            JS9.globalOpts.xeqPlugins = false;
            console.log("syncing colormap from ", im);
            partner = JS9p.get_partner_display(im);
            colormap = JS9.GetColormap({display:im});
            if( partner ) {
                JS9.SetColormap(colormap.colormap, colormap.contrast, colormap.bias, {display: partner});
                JS9p.display_props[im.display.id].colormap = colormap;
                JS9p.display_props[partner].colormap = colormap;
            }
            JS9.globalOpts.xeqPlugins = true;
        }
    }

    // load JS9 components
    var wrapper = document.createElement("div");
    wrapper.innerHTML = "\
      <link type='image/x-icon' rel='shortcut icon' href='/static/js9-www/favicon.ico'>\
      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9support.css'>\
      <link type='text/css' rel='stylesheet' href='/static/js9-www/js9.css'>\
      <link rel='apple-touch-icon' href='/static/js9-www/images/js9-apple-touch-icon.png'>\
      <script type='text/javascript' src='/static/js9-www/js9prefs.js'></script>\
      <script type='text/javascript' src='/static/js9-www/js9support.min.js'></script>\
      <script type='text/javascript' src='/static/js9-www/js9.min.js'></script>\
      <script type='text/javascript' src='/static/js9-www/js9plugins.js'></script>\
      <script type='text/javascript'> console.log('loaded JS9 components') </script>\
    "
    document.body.appendChild(wrapper);

    $(document).ready(function() {

        JS9.RegisterPlugin("MyPlugins", "update_zoom_region",
                   function(){return;},
                   {onregionschange: function(im, xreg) {
                        console.log("image is", im);
                        console.log("xreg is", xreg);
                        partner = JS9p.get_partner_display(im);
                        if( partner && xreg.data == "zoom_region" ) {
                            var prev_im = JS9.LookupImage(im.id, {display: partner})
                            if( prev_im ) {
                                JS9.CloseImage({clear:false},{display: prev_im});
                            }
                            JS9.Load(im.id, {fits2fits:true,
                                xcen:xreg.lcs.x,ycen:xreg.lcs.y,xdim:xreg.lcs.width,ydim:xreg.lcs.height,bin:1,
                                zoom:'T',onload:JS9p.reset_scale_colormap},
                                {display: partner});
                        }
                     },
                   winDims: [0, 0]});

        // syncs color settings between partner displays
        JS9.RegisterPlugin("MyPlugins", "allconstrastbias",
                   function(){return;},
                   {onchangecontrastbias: JS9p.sync_partner_colormaps,
                     winDims: [0, 0]});

        // syncs color settings between partner displays
        JS9.RegisterPlugin("MyPlugins", "allcolormap",
                   function(){return;},
                   {onsetcolormap:  JS9p.sync_partner_colormaps,
                     winDims: [0, 0]});

        // syncs scale settings between partner displays
        JS9.RegisterPlugin("MyPlugins", "allscale",
                   function(){return;},
                   {onsetscale: function(im){
                       console.log("syncing scale from ", im);
                       JS9.globalOpts.xeqPlugins = false;
                       scale = JS9.GetScale({display: im});
                       console.log("scale is", scale);
                       partner = JS9p.get_partner_display(im);
                       if( partner ) {
                           JS9.SetScale(scale.scale,scale.smin,scale.smax,{display: partner});
                           JS9p.display_props[im.display.id].scale = scale;
                           JS9p.display_props[partner].scale = scale;
                       }
                       JS9.globalOpts.xeqPlugins = true;
                   },
                   winDims: [0, 0]});
    })
}



     });

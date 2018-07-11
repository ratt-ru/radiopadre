// define JS9 radiopadre functionality
var JS9p = {
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

// register plugins

$(document).ready(function() {

    // if a region with data:"zoom_region" is moved on one display, and that display has a partner,
    // issue a JS9.Load() call on the partner display with corresponding fits2fits arguments
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

});

// include standard script library
// define JS9 radiopadre functionality

/*global JS9 */

var JS9p = {
    debug: true,
    display_props: {},
    // checks if the given display has a colormap and scale saved -- resets if if so
    reset_scale_colormap: function(im)
    {
	var colormap, scale;
        var props = JS9p.display_props[im.display.id];
        if( props ) {
            if( props.reset_scale_colormap ){
		return;
            }
            props.reset_scale_colormap = true;
	    //        JS9.globalOpts.xeqPlugins = false;
            colormap = props.colormap;
            scale = props.scale;
	    if( JS9p.debug ){
		// eslint-disable-next-line no-console
		console.log("saved scale and colormap",scale,colormap);
	    }
            if( colormap ) {
		if( JS9p.debug ){
		    // eslint-disable-next-line no-console
		    console.log("resetting colormap", colormap);
		}
		JS9.SetColormap(colormap.colormap,
				colormap.contrast,
				colormap.bias,
				{display: im});
            }
            if( scale ) {
		if( JS9p.debug ){
		    // eslint-disable-next-line no-console
		    console.log("resetting scale", scale);
		}
		JS9.SetScale(scale.scale,
			     scale.scalemin,
			     scale.scalemax,
			     {display: im});
            }
	    //        JS9.globalOpts.xeqPlugins = true;
            delete props.reset_scale_colormap;
        }
    },
    // registers two displays as partnered
    register_partners: function(d1, d2)
    {
        JS9p.display_props[d1] = {partner_display: d2};
        JS9p.display_props[d2] = {partner_display: d1};
    },
    // if display of image im has a partner, return it
    get_partner_display: function(im)
    {
        var props = JS9p.display_props[im.display.id];
        return props ? props.partner_display : false;
    },
    // if display of image im has a partner, syncs colormap to it
    sync_partner_colormaps: function (im)
    {
	//      JS9.globalOpts.xeqPlugins = false;
	var partner, colormap;
        var props = JS9p.display_props[im.display.id];
        if( props.sync_partner_colormaps ){
            return;
        }
        props.sync_partner_colormaps = true;
	if( JS9p.debug ){
	    // eslint-disable-next-line no-console
            console.log("syncing colormap from ", im);
	}
        partner = JS9p.get_partner_display(im);
        colormap = JS9.GetColormap({display:im});
        if( partner ) {
            JS9.SetColormap(colormap.colormap,
			    colormap.contrast,
			    colormap.bias,
			    {display: partner});
            JS9p.display_props[im.display.id].colormap = colormap;
            JS9p.display_props[partner].colormap = colormap;
        }
	//      JS9.globalOpts.xeqPlugins = true;
        delete props.sync_partner_colormaps;
    },
    // if display of image im has a partner, syncs scale to it
    sync_partner_scales: function (im)
    {
	//      JS9.globalOpts.xeqPlugins = false;
	var partner, scale;
        var props = JS9p.display_props[im.display.id];
        if( props.sync_partner_scales ){
            return;
        }
        props.sync_partner_scales = true;
	if( JS9p.debug ){
	    // eslint-disable-next-line no-console
            console.log("syncing scale from ", im);
	}
        partner = JS9p.get_partner_display(im);
        scale = JS9.GetScale({display:im});
        if( partner ) {
            JS9.SetScale(scale.scale,
			 scale.scalemin,
			 scale.scalemax,
			 {display: partner});
            JS9p.display_props[im.display.id].scale = scale;
            JS9p.display_props[partner].scale = scale;
        }
	//      JS9.globalOpts.xeqPlugins = true;
        delete props.sync_partner_scales;
    },
    load_partner: function(im, xreg)
    {
	var partner = JS9p.get_partner_display(im);
	if( partner && xreg.data === "zoom_region" ) {
            if( JS9p.debug ){
                // eslint-disable-next-line no-console
                console.log("zoom-syncing", im, xreg);
            }
            JS9.CloseImage({clear:false},{display: partner});
            JS9.Load(im.id, {fits2fits:true,
			     xcen:xreg.lcs.x,
			     ycen:xreg.lcs.y,
			     xdim:xreg.lcs.width,
			     ydim:xreg.lcs.height,
			     bin:1,
			     zoom:'T',
			     onload: JS9p.reset_scale_colormap},
		     {display: partner});
	}
    }
};

$(document).ready(function() {
    if( JS9p.debug ){
        // eslint-disable-next-line no-console
        console.log("registering JS9 partner display plug-in");
    }
    // syncs color settings between partner displays
    JS9.RegisterPlugin("MyPlugins", "partner",
                       function(){return;},
                       {onchangecontrastbias: JS9p.sync_partner_colormaps,
                        onsetcolormap:  JS9p.sync_partner_colormaps,
                        onsetscale: JS9p.sync_partner_scales,
                        onregionschange: JS9p.load_partner,
                        winDims: [0, 0]});
})

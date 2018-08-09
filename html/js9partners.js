// include standard script library
// define JS9 radiopadre functionality

/*global JS9 */

function JS9p_PartneredDisplays(display_id)
{
    this.outer = document.getElementById('outer-' + display_id)
    this.disp_rebin = 'rebin-' + display_id + '-JS9'
    this.disp_zoom  = 'zoom-'  + display_id + '-JS9'
    this.status = document.getElementById('status-' + display_id)

    JS9p.display_props[this.disp_rebin] = {partnership:this, partner_display: this.disp_zoom}
    JS9p.display_props[this.disp_zoom]  = {partnership:this, partner_display: this.disp_rebin}

    JS9.AddDivs(this.disp_rebin, this.disp_zoom)
}

JS9p_PartneredDisplays.prototype.setStatus = function(status)
{
    if( JS9p.debug ) {
        console.log('JS9p_PartneredDisplays status:', status);
    }
    this.status.innerHTML = status
}

JS9p_PartneredDisplays.prototype.loadImage = function(path,xsz,ysz,zoombox,bin)
{
    this.setStatus("Loading "+path+" preview, please wait...")
    JS9.Load(path, {fits2fits:true, xcen:(xsz/2>>0), ycen:(ysz/2>>0), xdim:xsz, ydim:ysz, bin:bin,
                    onload: im => this.onLoadRebin(im, zoombox),
                    zoom:'T'},
                   {display:this.disp_rebin});
    // document.getElementById('outer-{display_id}').style.height = '60vw'
    this.outer.style.display = 'block'
}

JS9p_PartneredDisplays.prototype.onLoadRebin = function(im, zoombox)
{
    if( JS9p.debug ) {
            console.log('loaded image', im, 'into rebinned view');
        }
    JS9.AddRegions(zoombox,
                   {color:'red',data:'zoom_region',rotatable:false,removable:false},
                   {display:this.disp_rebin})
    im._js9p_partnered_displays = this
    this.setStatus(`Loaded preview image for ${im.id}`)
}

JS9p_PartneredDisplays.prototype.onLoadZoom = function(im)
{
    JS9p.reset_scale_colormap(im)
    this.setStatus(`Loaded ${im.id} (slice ${xreg.lcs.width}x${xreg.lcs.height}@${xreg.lcs.x},${xreg.lcs.y})`)
}

JS9p_PartneredDisplays.prototype.check_zoom_region = function(im, xreg)
{
    if( im.display == this.disp_rebin && xreg.data === "zoom_region" ) {
        if( JS9p.debug ){
            // eslint-disable-next-line no-console
            console.log("zoom-syncing", im, xreg);
        }
        JS9.CloseImage({clear:false},{display: this.disp_zoom});
        this.setStatus(`Loading ${im.id} (slice ${xreg.lcs.width}x${xreg.lcs.height}@${xreg.lcs.x},${xreg.lcs.y}), please wait...`)

        JS9.Load(im.id, {fits2fits:true,
                             xcen:xreg.lcs.x,
                             ycen:xreg.lcs.y,
                             xdim:xreg.lcs.width,
                             ydim:xreg.lcs.height,
                             bin:1,
                             zoom:'T',
                             onload: this.onLoadZoom
                         },
                 {display: this.disp_zoom});
    }
}

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
    check_zoom_region: function(im, xreg)
    {
        console.log(im, im._js9p_partnered_displays, xreg)
        partners = im._js9p_partnered_displays
        if( partners )
            partners.check_zoom_region(im, xreg)
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
                        onregionschange: JS9p.check_zoom_region,
                        winDims: [0, 0]});
})

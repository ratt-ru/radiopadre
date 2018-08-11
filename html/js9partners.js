// include standard script library
// define JS9 radiopadre functionality

/*global JS9 */

function JS9pTuple(x,y)
{
    this.x = x
    this.y = y
}

function JS9pImageProps(displays, xsz, ysz, xzoom, yzoom)
{
    this.partnered_displays = displays
    this.size = new JS9pTuple(xsz, ysz)
    this.zoomsize = new JS9pTuple(Math.min(xzoom,xsz), Math.min(yzoom,ysz))
    dx = this.zoomsize.x/2>>0
    dy = this.zoomsize.y/2>>0
    this.zoom_min = new JS9pTuple(dx, dy)
    this.zoom_max = new JS9pTuple(xsz-dx, ysz-dy)
    this.zoombox = { shape:"box", x:0, y:0, width:this.zoomsize.x, height:this.zoomsize.y, tags:"zoombox",
                     color:'red',data:'zoom_region',rotatable:false,removable:false,tags:"zoombox" }
}

JS9pImageProps.prototype.updateZoom = function(x,y)
{
    x = Math.max(Math.min(x>>0, this.zoom_max.x), this.zoom_min.x)
    y = Math.max(Math.min(y>>0, this.zoom_max.y), this.zoom_min.y)
    this.zoombox.x = x
    this.zoombox.y = y
    this.zoombox_str = `box(${x},${y},${this.zoombox.width},${this.zoombox.height},0)`
    return this.zoombox
}


function JS9pPartneredDisplays(display_id, zoomsize)
{
    this.outer = document.getElementById('outer-' + display_id)
    this.disp_rebin = 'rebin-' + display_id + '-JS9'
    this.disp_zoom  = 'zoom-'  + display_id + '-JS9'
    this.status = document.getElementById('status-' + display_id)
    this.zoomsize = zoomsize

    JS9p.display_props[this.disp_rebin] = {partnership:this, partner_display: this.disp_zoom}
    JS9p.display_props[this.disp_zoom]  = {partnership:this, partner_display: this.disp_rebin}

    JS9.AddDivs(this.disp_rebin, this.disp_zoom)
}

JS9pPartneredDisplays.prototype.setStatus = function(status)
{
    if( JS9p.debug ) {
        console.log('JS9pPartneredDisplays status:', status);
    }
    this.status.innerHTML = status
}

JS9pPartneredDisplays.prototype.loadImage = function(path, xsz, ysz, bin)
{
    this.setStatus(`Loading ${path} preview image, please wait...`)
    JS9.Load(path, {fits2fits:true, xcen:(xsz/2>>0), ycen:(ysz/2>>0), xdim:xsz, ydim:ysz, bin:bin,
                    onload: im => this.onLoadRebin(im, xsz, ysz),
                    zoom:'T'},
                   {display:this.disp_rebin});
    // document.getElementById('outer-{display_id}').style.height = '60vw'
    this.outer.style.display = 'block'
}

JS9pPartneredDisplays.prototype.onLoadRebin = function(im, xsz, ysz)
{
    if( JS9p.debug ) {
            console.log('loaded image', im, 'into rebinned view', this);
        }
    this.setStatus(`Loaded preview image for ${im.id}`)
    im._js9p = new JS9pImageProps(this, xsz, ysz, this.zoomsize, this.zoomsize)
    zoombox = im._js9p.updateZoom(xsz/2, ysz/2)
    console.log("setting zoombox", zoombox)
    // JS9.AddRegions(zoombox, {}, {display:this.disp_rebin})
    JS9.AddRegions(im._js9p.zoombox_str, zoombox, {display:this.disp_rebin})
}

JS9pPartneredDisplays.prototype.onLoadZoom = function(im)
{
    console.log(this)
    JS9p.reset_scale_colormap(im)
    this.setStatus(`Loaded ${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} slice at ${imp.zoombox.x},${imp.zoombox.y})`)
}

JS9pPartneredDisplays.prototype.checkZoomRegion = function(im, xreg)
{
    if( im.display.id == this.disp_rebin && xreg.tags.indexOf("zoombox")>-1 && !this._in_checkzoom) {
        this._in_checkzoom = true
        if( JS9p.debug ){
            // eslint-disable-next-line no-console
            console.log("zoom-syncing", im, xreg);
        }
        imp = im._js9p
        // make sure region is within bounds
        zoombox = imp.updateZoom(xreg.lcs.x, xreg.lcs.y)
        console.log(zoombox)
        JS9.CloseImage({clear:false},{display: this.disp_zoom});
        this.setStatus(`Loading ${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} slice at ${imp.zoombox.x},${imp.zoombox.y}), please wait...`)
        JS9.Load(im.id, {fits2fits:true,
                             xcen: imp.zoombox.x,
                             ycen: imp.zoombox.y,
                             xdim: imp.zoomsize.x,
                             ydim: imp.zoomsize.y,
                             bin:1,
                             zoom:'T',
                             onload: im => this.onLoadZoom(im)
                         },
                 {display: this.disp_zoom});
//        JS9.RemoveRegions("all", {display:this.disp_rebin})
//        JS9.AddRegions(im._js9p.zoombox_str, zoombox, {display:this.disp_rebin})
        JS9.ChangeRegions("all", zoombox, {display:this.disp_rebin})
        this._in_checkzoom = false
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
        if( im._js9p && im._js9p.partnered_displays )
            im._js9p.partnered_displays.checkZoomRegion(im, xreg)
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

// include standard script library
// define JS9 radiopadre functionality

/*global JS9 */

function JS9pTuple(x,y)
{
    this.x = x
    this.y = y
}

function JS9pImageProps(displays, xsz, ysz, bin, xzoom, yzoom)
{
    this.partnered_displays = displays
    this.size = new JS9pTuple(xsz, ysz)                                            // full image size
    this.bin  = bin
    this.zoomsize  = new JS9pTuple(Math.min(xzoom,xsz), Math.min(yzoom,ysz))       // zoomed section size (full res)
    this.zoomsize1 = new JS9pTuple(this.zoomsize.x/bin>>0, this.zoomsize.y/bin>>0) // zoomed section size (rebinned res)
    this.zoom_cen  = new JS9pTuple(this.size.x/2>>0, this.size.y/2>>0)             // zoomed section centre (full res)
    // min/max possible center of zoom region, at rebinned resolution
    var dx = this.zoomsize.x/2>>0
    var dy = this.zoomsize.y/2>>0
    this.zoom_min = new JS9pTuple(dx/bin>>0, dy/bin>>0)
    this.zoom_max = new JS9pTuple((xsz-dx)/bin>>0, (ysz-dy)/bin>>0)
    // zoombox region, at rebinned resolution
    this.zoombox = { shape:"box", x:0, y:0, width:this.zoomsize1.x, height:this.zoomsize1.y,
                     color:'red',data:'zoom_region',rotatable:false,removable:false,tags:"zoombox" }
}

JS9pImageProps.prototype.restrictZoombox = function(x,y)
{
    var x = Math.max(Math.min(x>>0, this.zoom_max.x), this.zoom_min.x)
    var y = Math.max(Math.min(y>>0, this.zoom_max.y), this.zoom_min.y)
    this.zoombox.x = x
    this.zoombox.y = y
}

JS9pImageProps.prototype.updateZoombox = function(x,y)
{
    this.restrictZoombox(x,y)
    var x1 = this.zoombox.x*this.bin
    var y1 = this.zoombox.y*this.bin
    if( x1 != this.zoom_cen.x || y1 != this.zoom_cen.y ) {
        this.zoom_cen.x = x1
        this.zoom_cen.y = y1
        return true
    }
    return false
}


function JS9pPartneredDisplays(display_id, zoomsize)
{
    this.outer = document.getElementById('outer-' + display_id)
    this.disp_rebin = 'rebin-' + display_id + '-JS9'
    this.disp_zoom  = 'zoom-'  + display_id + '-JS9'
    this.status = document.getElementById('status-' + display_id)
    this.status_rebin = document.getElementById('status-' + display_id + '-rebin')

    this.zoomsize = zoomsize

    JS9p.display_props[this.disp_rebin] = {partnership:this, partner_display: this.disp_zoom}
    JS9p.display_props[this.disp_zoom]  = {partnership:this, partner_display: this.disp_rebin}

    JS9.AddDivs(this.disp_rebin, this.disp_zoom)
}

JS9pPartneredDisplays.prototype.setStatus = function(status)
{
    JS9p.log('JS9pPartneredDisplays status:', status);
    if( this.status )
        this.status.innerHTML = status
}

JS9pPartneredDisplays.prototype.setStatusRebin = function(status)
{
    JS9p.log('JS9pPartneredDisplays rebin status:', status);
    if( this.status_rebin )
        this.status_rebin.innerHTML = status
}

JS9pPartneredDisplays.prototype.setDefaultImageOpts = function(opts)
{
    if( this.default_scale != null )
        opts.scale = this.default_scale
    if( this.default_colormap != null )
        opts.colormap = this.default_colormap
}

JS9pPartneredDisplays.prototype.loadImage = function(path, xsz, ysz, bin, average)
{
    this.setStatus(`Loading ${path} (downsampled preview), please wait...`)
    this.setStatusRebin("Loading preview...")
    this.bin = bin
    var binopt = average ? `${bin}a` : `${bin}`
    var opts = {fits2fits:true, xcen:(xsz/2>>0), ycen:(ysz/2>>0), xdim:xsz, ydim:ysz, bin:binopt,
                onload: im => this.onLoadRebin(im, xsz, ysz, bin),
                zoom: 'T', valpos: false}
    this.setDefaultImageOpts(opts)
    JS9p.log("Loading", path, "with options", opts)
    JS9.Load(path, opts, {display:this.disp_rebin});
    // document.getElementById('outer-{display_id}').style.height = '60vw'
    this.outer.style.display = 'block'
}

JS9pPartneredDisplays.prototype.onLoadRebin = function(im, xsz, ysz, bin)
{
    im._js9p = new JS9pImageProps(this, xsz, ysz, bin, this.zoomsize, this.zoomsize)
    this.resetScaleColormap(im)
    this.setStatus(`Loaded preview image for ${im.id}`)
    this.setStatusRebin("Drag region to load")
    im._js9p.updateZoombox(xsz/bin/2, ysz/bin/2)
    JS9p.log("setting zoombox", im._js9p.zoombox)
    im._js9p.zoom_cen.x = null // to force an update
    JS9.AddRegions(im._js9p.zoombox, {}, {display:this.disp_rebin})
}

JS9pPartneredDisplays.prototype.onLoadZoom = function(im, imp)
{
    im._js9p = imp
    this.resetScaleColormap(im)
    JS9.ChangeRegions("all", imp.zoombox, {display:this.disp_rebin})
    this.setStatus(`${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} region at ${imp.zoom_cen.x},${imp.zoom_cen.y})`)
    this.setStatusRebin("Drag region to load")
    delete this._disable_checkzoom
}

JS9pPartneredDisplays.prototype.resetScaleColormap = function(im)
{
    this._setting_scales_colormaps = true
    if( this.user_colormap != null ) {
        JS9p.log("setting user-defined colormap", this.user_colormap);
        JS9.SetColormap(this.user_colormap.colormap,
                        this.user_colormap.contrast,
                        this.user_colormap.bias,
                        {display: im})
    }
    else if( this.default_colormap != null ) {
        JS9p.log("setting default colormap", this.default_colormap);
        JS9.SetColormap(this.default_colormap, 1, 0.5, {display: im})
    }
    if( this.user_scale != null ) {
        JS9p.log("setting user-defined scale", this.scale);
        JS9.SetScale(this.user_scale.scale,
                     this.user_scale.scalemin,
                     this.user_scale.scalemax,
                     {display: im})
    }
    else if( this.default_scale != null || this.default_vmin != null || this.default_vmax != null) {
        scale = JS9.GetScale({display: im})
        if( this.default_scale != null )
            scale.scale = this.default_scale
        if( this.default_vmin != null )
            scale.scalemin = this.default_vmin
        if( this.default_vmax != null )
            scale.scalemax = this.default_vmax
        JS9.SetScale(scale.scale,
                     scale.scalemin,
                     scale.scalemax,
                     {display: im})
    }
    delete this._setting_scales_colormaps
}

JS9pPartneredDisplays.prototype.syncColormap = function(im)
{
    if( this._setting_scales_colormaps )
        return
    this._setting_scales_colormaps = true
    var partner = im.display.id == this.disp_rebin ? this.disp_zoom : this.disp_rebin
    this.user_colormap = JS9.GetColormap({display:im})
    JS9p.log(`syncing colormap from ${im} to display ${partner}`)
    JS9.SetColormap(this.user_colormap.colormap,
                    this.user_colormap.contrast,
                    this.user_colormap.bias,
                    {display: partner})
    delete this._setting_scales_colormaps
}

JS9pPartneredDisplays.prototype.syncScale = function(im)
{
    if( this._setting_scales_colormaps )
        return
    this._setting_scales_colormaps = true
    var partner = im.display.id == this.disp_rebin ? this.disp_zoom : this.disp_rebin
    this.user_scale = JS9.GetScale({display:im});
    JS9p.log(`syncing colormap from ${im} to display ${partner}`)
    JS9.SetScale(this.user_scale.scale,
                 this.user_scale.scalemin,
                 this.user_scale.scalemax,
                 {display: partner});
    delete this._setting_scales_colormaps
}

JS9pPartneredDisplays.prototype.checkZoomRegion = function(im, xreg)
{
    if( im.display.id == this.disp_rebin && xreg.tags.indexOf("zoombox")>-1 && !this._disable_checkzoom)
    {
        JS9p.log("checkZoomRegion", im, xreg);
        this._disable_checkzoom = true
        if( JS9p.debug ){
            // eslint-disable-next-line no-console
            console.log("zoom-syncing", im, xreg);
        }
        var imp = im._js9p
        // make sure region is within bounds
        var updated = imp.updateZoombox(xreg.x, xreg.y)
        JS9.ChangeRegions("all", imp.zoombox, {display:this.disp_rebin})
        if( updated ) {
            JS9.CloseImage({clear:false},{display: this.disp_zoom});
            this.setStatus(`Loading ${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} region at ${imp.zoom_cen.x},${imp.zoom_cen.y}), please wait...`)
            this.setStatusRebin("Loading region...")
            opts = { fits2fits:true,
                     xcen: imp.zoom_cen.x,
                     ycen: imp.zoom_cen.y,
                     xdim: imp.zoomsize.x,
                     ydim: imp.zoomsize.y,
                     bin:1,
                     zoom:'T',
                     onload: im => this.onLoadZoom(im, imp, imp.zoombox)
                 }
            this.setDefaultImageOpts(opts)
            JS9.Load(im.id, opts, {display: this.disp_zoom});
        }
        else
            delete this._disable_checkzoom
        // this will be done in the callback, ignore region events until then: delete this._disable_checkzoom
    }
}

JS9pPartneredDisplays.prototype.moveZoomRegion = function(im, xreg)
{
    if( im.display.id == this.disp_rebin && xreg.tags.indexOf("zoombox")>-1 ) {
        var imp = im._js9p
        // make sure region is within bounds
        imp.restrictZoombox(xreg.x, xreg.y)
        xreg.x = imp.zoombox.x
        xreg.y = imp.zoombox.y
        JS9p.log("moveZoomRegion enforcing",xreg.x,xreg.y)
    }
}


var JS9p = {
    debug: true,

    display_props: {},

    log: function(...args)
    {
        if( JS9p.debug )
            console.log(...args)
    },

    call_partner_method: function(method, im, ...args)
    {
        if( im._js9p && im._js9p.partnered_displays )
            im._js9p.partnered_displays[method](im, ...args)
    }
};

$(document).ready(function() {

    JS9p.log("registering JS9 partner display plug-in")

    // syncs color settings between partner displays
    JS9.RegisterPlugin("MyPlugins", "partner",
                       function(){return;},
                       {onchangecontrastbias:   im => JS9p.call_partner_method("syncColormap", im),
                        onsetcolormap:          im => JS9p.call_partner_method("syncColormap", im),
                        onsetscale:             im => JS9p.call_partner_method("syncScale", im),
                        onregionschange:        (im,xreg) => JS9p.call_partner_method("checkZoomRegion", im, xreg),
                        onregionsmove:          (im,xreg) => JS9p.call_partner_method("moveZoomRegion", im, xreg),
                        winDims: [0, 0]});
})

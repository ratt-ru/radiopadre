//
// JS9pTuple: a very simple object to hold an x,y position
//
function JS9pTuple(x,y)
{
    this.x = x
    this.y = y
}

//
// JS9pImageProps: image properties for a FITS image loaded into JS9pPartneredDisplays.
//                 For each loaded JS9 image, a _js9p property will be created with this object in it.
//
function JS9pImageProps(displays, xsz, ysz, bin, xzoom, yzoom)
{
    // parent partnered_displays object
    this.partnered_displays = displays
    // full image size in pixels
    this.size = new JS9pTuple(xsz, ysz)
    // binning factor of preview image
    this.bin  = bin
    // size of zoomed section, in full-resolution pixels
    this.zoomsize  = new JS9pTuple(Math.min(xzoom,xsz), Math.min(yzoom,ysz))       // zoomed section size (full res)
    // size of zoomed section, in rebinned pixels
    this.zoomsize1 = new JS9pTuple(this.zoomsize.x/bin>>0, this.zoomsize.y/bin>>0) // zoomed section size (rebinned res)
    // centre of zoomed section, in full-res pixel coordinates
    this.zoom_cen  = new JS9pTuple(this.size.x/2>>0, this.size.y/2>>0)             // zoomed section centre (full res)
    // limits for center of zoomed region, in rebinned pixel coordinates
    var dx = this.zoomsize.x/2>>0
    var dy = this.zoomsize.y/2>>0
    this.zoom_min = new JS9pTuple(dx/bin>>0, dy/bin>>0)
    this.zoom_max = new JS9pTuple((xsz-dx)/bin>>0, (ysz-dy)/bin>>0)
    // zoombox: this is a JS9 region object describing the zoomed region
    this.zoombox = { shape:"box", x:0, y:0, width:this.zoomsize1.x, height:this.zoomsize1.y,
                     color:'red',data:'zoom_region',rotatable:false,removable:false,tags:"zoombox" }
}

// Sets center of zoombox to x,y, applying the zoombox region limits
JS9pImageProps.prototype.restrictZoombox = function(x,y)
{
    var x = Math.max(Math.min(x>>0, this.zoom_max.x), this.zoom_min.x)
    var y = Math.max(Math.min(y>>0, this.zoom_max.y), this.zoom_min.y)
    this.zoombox.x = x
    this.zoombox.y = y
    return this.zoombox
}

// Sets center of zoombox to x,y, applying the zoombox region limits,
// aand also updates the zoom_cen property. Returns true if center has changed.
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


//
// JS9pPartneredDisplays: class supporting two "partnered" JS9 displays. One display shows a rebinned preview image
// and a zoombox. The second display shows the section of the image given by the zoombox, at full resolution.
//
// The following DIV elements are expected to exist in the DOM (where "DISPLAY" is a unique display ID)
//
// outer-DISPLAY                    # outer element containing the partner displays
//      rebin-DISPLAY-outer         # outer element containing preview display
//          rebin-DISPLAY-JS9       # JS9 window for preview image
//      zoom-DISPLAY-JS9            # JS9 window for zoomed section
//      status-DISPLAY              # text element where full status messages are displayed (optional)
//      status-DISPLAY-rebin        # text element where smaller status messages are displayed (for preview status, optional)
//
// Arguments are: display_id, xzoom, yzoom. The latter two give the default size of the zoomed region.
//
function JS9pPartneredDisplays(display_id, xzoom, yzoom)
{
    this.outer_div = document.getElementById('outer-' + display_id)
    this.rebin_div = document.getElementById('rebin-' + display_id + '-outer')
    this.disp_rebin = 'rebin-' + display_id + '-JS9'
    this.disp_zoom  = 'zoom-'  + display_id + '-JS9'
    this.status = document.getElementById('status-' + display_id)
    this.status_rebin = document.getElementById('status-' + display_id + '-rebin')

    this.zoomsize = new JS9pTuple(xzoom, yzoom)

    // object of default display settings (vmin/vmax, colormap, etc.)
    this.defaults = {}

    JS9p.display_props[this.disp_rebin] = {partnership:this, partner_display: this.disp_zoom}
    JS9p.display_props[this.disp_zoom]  = {partnership:this, partner_display: this.disp_rebin}

    JS9.AddDivs(this.disp_rebin, this.disp_zoom)
}

// loadImage(path,xsize,ysize,bin,average)
//      Loads an image into the partner displays.
//      Path is image path/URL. xsz/ysz is the full image size. Bin is the rebinning factor for the preview image.
//      Average is true to average, false to sum.
//
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
    JS9.Preload(path, opts, {display:this.disp_rebin});
    // make the outer element visible
    this.outer_div.style.display = 'block'
}


// setStatus(message)
//      Displays status message in the status element
//
JS9pPartneredDisplays.prototype.setStatus = function(status)
{
    JS9p.log('JS9pPartneredDisplays status:', status);
    if( this.status )
        this.status.innerHTML = status
}

// setStatusRebin(message)
//      Displays status message in the preview image's status element
//
JS9pPartneredDisplays.prototype.setStatusRebin = function(status)
{
    JS9p.log('JS9pPartneredDisplays rebin status:', status);
    if( this.status_rebin )
        this.status_rebin.innerHTML = status
}

// setDefaultImageOpts(opts)
//      Populates the opts object with default set of options to be passed to JS9.Load() or JS9.Preload()
//      Used to set the image scale, colormap, etc.
//      Called internally before loading an image.
//
JS9pPartneredDisplays.prototype.setDefaultImageOpts = function(opts)
{
    if( this.defaults.scale != null )
        opts.scale = this.defaults.scale
    if( this.defaults.colormap != null )
        opts.colormap = this.defaults.colormap
}

// onLoadRebin(im, xsz, ysz, bin)
//      Callback invoked when the preview image has been loaded.
//      im is JS9 image (rebinned). xsz/ysz/bin arguments are as passed to loadImage()
//
JS9pPartneredDisplays.prototype.onLoadRebin = function(im, xsz, ysz, bin)
{
    this.setStatus(`Loaded preview image for ${im.id}`)
    JS9p.log(this)
    im._js9p = new JS9pImageProps(this, xsz, ysz, bin, this.zoomsize.x, this.zoomsize.y)
    this.resetScaleColormap(im)
    this.setStatusRebin("Drag region to load")
    im._js9p.updateZoombox(xsz/bin/2, ysz/bin/2)
    JS9p.log("setting zoombox", im._js9p.zoombox)
    im._js9p.zoom_cen.x = null // to force an update
    JS9.AddRegions(im._js9p.zoombox, {}, {display:this.disp_rebin})
}

// onLoadZoom(im, imp)
//      Callback invoked when the preview image has been loaded.
//      im is JS9 image (zoomed). imp is an JS9pImageProperties object.
//
JS9pPartneredDisplays.prototype.onLoadZoom = function(im, imp)
{
    im._js9p = imp
    this.resetScaleColormap(im)
    JS9.ChangeRegions("all", imp.zoombox, {display:this.disp_rebin})
    this.setStatus(`${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} region at ${imp.zoom_cen.x},${imp.zoom_cen.y})`)
    this.setStatusRebin("Drag region to load")
    delete this._disable_checkzoom
}

// resetScaleColormap(im)
//      Sets the scale and colormap of a loaded image. Ensures that either defaults or previous user settings
//      for scales and colormaps are applied. Called internally from the onLoadXXX() callbacks.
//
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
    else if( this.defaults.colormap != null ) {
        JS9p.log("setting default colormap", this.defaults.colormap);
        JS9.SetColormap(this.defaults.colormap, 1, 0.5, {display: im})
    }
    if( this.user_scale != null ) {
        JS9p.log("setting user-defined scale", this.scale);
        JS9.SetScale(this.user_scale.scale,
                     this.user_scale.scalemin,
                     this.user_scale.scalemax,
                     {display: im})
    }
    else if( this.defaults.scale != null || this.defaults.vmin != null || this.defaults.vmax != null) {
        scale = JS9.GetScale({display: im})
        if( this.defaults.scale != null )
            scale.scale = this.defaults.scale
        if( this.defaults.vmin != null )
            scale.scalemin = this.defaults.vmin
        if( this.defaults.vmax != null )
            scale.scalemax = this.defaults.vmax
        JS9.SetScale(scale.scale,
                     scale.scalemin,
                     scale.scalemax,
                     {display: im})
    }
    delete this._setting_scales_colormaps
}

// syncColormap(im)
//      Internal callback for when the colormap of an image is changed. Propagates changes to other display,
//      and saves them for future images
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

// syncScale(im)
//      Internal callback for when the scale of an image is changed. Propagates changes to other display,
//      and saves them for future images
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

// checkZoomRegion(im, xreg)
//      Internal callback for when regions are changed. Checks if the region is the zoombox, and causes
//      a new section of the zoomed image to be loaded if so
//
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
            JS9p.log("preloading", opts)
            JS9.Preload(im.id, opts, {display: this.disp_zoom});
        }
        else
            delete this._disable_checkzoom
        // this will be done in the callback, ignore region events until then: delete this._disable_checkzoom
    }
}

// checkZoomRegion(im, xreg)
//      Internal callback for when regions are moved.
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


// JS9p: namespace for partner displays, and associated code
//
var JS9p = {
    // if True, various stuff is logged to console.log()
    debug: true,

    // display properties, used by JS9pPartneredDisplays
    display_props: {},

    // log(...)
    //      logs stuff to console (if debug==True), else does nothing
    log: function(...args)
    {
        if( JS9p.debug )
            console.log(...args)
    },

    // call_partner_method()
    //      Generic callback mechanism. If image has a partnered displays object associated with it,
    //      invokes the given method of that object, with the remaining arguments.
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

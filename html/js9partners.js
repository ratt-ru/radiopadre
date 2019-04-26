//
//
// JS9pTuple: a very simple object to hold an x,y position
//
function JS9pTuple(x,y)
{
    this.x = x
    this.y = y
}

JS9pTuple.prototype.equals = function(x,y) {
    if( x == null )
        return false
    if( y == null )
        return this.x == x.x && this.y == x.y
    return this.x == x && this.y == y
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
    // centre pixel of full image (rounded to whole pixel)
    this.centre = new JS9pTuple(xsz/2>>0, ysz/2>>0)
    // binning factor of preview image
    this.bin  = bin
    // flag: is the image zoomable at all
    this.zoomable = (xsz>xzoom || ysz>yzoom)
    if( this.zoomable )
    {
        // size of zoomed section, in full-resolution pixels
        this.zoomsize  = new JS9pTuple(Math.min(xzoom,xsz), Math.min(yzoom,ysz))       // zoomed section size (full res)
        // size of zoomed section, in rebinned pixels
        this.zoomsize1 = new JS9pTuple(this.zoomsize.x/bin, this.zoomsize.y/bin)       // zoomed section size (rebinned res)
        // centre of zoomed section, in full-res pixel coordinates, relative to image centre
        this.zoom_rel  = new JS9pTuple(0,0)
        // limits for center of zoomed region, in full-resolution pixels
        var dx = this.zoomsize.x/2>>0
        var dy = this.zoomsize.y/2>>0
        this.zoom_min = new JS9pTuple(dx, dy)
        this.zoom_max = new JS9pTuple(xsz-dx, ysz-dy)
        // zoombox: this is a JS9 region object describing the zoomed region in rebinned coordinates. x/y set in updateZoombox()
        this.zoombox = { shape:"box", x:0, y:0, width:this.zoomsize1.x, height:this.zoomsize1.y,
                         color:'red',data:'zoom_region',movable:true,rotatable:false,removable:false,tags:"zoombox" }
    }
}

// Sets center of zoombox based on x/y full-res coordinates, applying the zoom region limits
JS9pImageProps.prototype.restrictZoombox = function(x,y)
{
    var x = Math.max(Math.min(x>>0, this.zoom_max.x), this.zoom_min.x)
    var y = Math.max(Math.min(y>>0, this.zoom_max.y), this.zoom_min.y)
    this.zoombox.x = x/this.bin
    this.zoombox.y = y/this.bin
    return this.zoombox
}

// Sets zoom centre based on x/y full-res coordinates, applying the zoom region limits.
// Changes the zoombox object, and also sets the relative zoom centre.
// Returns the new effective zoom centre, in full-res coordinates
JS9pImageProps.prototype.updateZoombox = function(x, y)
{
    this.restrictZoombox(x,y)
    var x1 = this.zoombox.x*this.bin>>0
    var y1 = this.zoombox.y*this.bin>>0
    this.zoom_rel.x = x1 - this.centre.x
    this.zoom_rel.y = y1 - this.centre.y
    return new JS9pTuple(x1, y1)
}

// Sets center of zoombox to coordinates relative to centre (in full resolution)
// Returns the zoom centre, in full-res coordinates
JS9pImageProps.prototype.updateZoomboxRel = function(rel)
{
    return this.updateZoombox(this.centre.x + rel.x, this.centre.y + rel.y)
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
    this.rebin_div = document.getElementById('rebin-' + display_id + "-outer")
    if( this.rebin_div )
        this.rebin_div_background = this.rebin_div.style.background
    this.disp_rebin = 'rebin-' + display_id + '-JS9'
    this.disp_zoom  = 'zoom-'  + display_id + '-JS9'
    this.status = document.getElementById('status-' + display_id)
    this.status_rebin = document.getElementById(`status-${display_id}-rebin`)
    this.w_reset_scale = document.getElementById(`zoom-${display_id}-fullscale`)
    if( this.w_reset_scale )
        this.w_reset_scale.onclick = ev => this.resetScaleColormap()
    this.w_lock_scale = document.getElementById(`zoom-${display_id}-lockscale`)
    if( this.w_lock_scale ) {
        this.w_lock_scale.style.visibility = "hidden"
        this.w_lock_scale.onclick = ev => this.toggleScaleColormapLock()
    }

    // toggle to false
    this.lock_scale = true
    this.toggleScaleColormapLock()
    // toggle to true
    this.lock_pan_zoom = false
    this.togglePanZoomLock()

    this.zoomsize = new JS9pTuple(xzoom, yzoom)

    // current zoom centre, relative to image centre. When switching images, this will be preserved as much as possible.
    this.zoom_rel = new JS9pTuple(0, 0)

    // object of default display settings (vmin/vmax, colormap, etc.)
    this.defaults = {}

    // keeps track of which image is displayed on top, when using multiple images
    this.current_image = {}
    this._current_zoompan = null

    // keeps track of loaded images
    this.imps = {}
    this._num_images = 0

    // queue of images to be loaded
    this._loading_queue = []

    JS9.AddDivs(this.disp_rebin, this.disp_zoom)
}

// loadImage(path,xsize,ysize,bin,average)
//      Loads an image into the partner displays.
//      Path is image path/URL. xsz/ysz is the full image size. Bin is the rebinning factor for the preview image.
//      Average is true to average, false to sum.
//
JS9pPartneredDisplays.prototype.loadImage = function(path, xsz, ysz, bin, average)
{
    // make the outer element visible
    this.outer_div.style.display = 'block'
    // queue up multiple loads, since we only process one at a time
    if( this._loading )
    {
        this._loading_queue.push({path:path, xsz:xsz, ysz:ysz, bin:bin, average: average})
        return
    }
    // show the scale lock button, if multiple images loaded
    this._num_images++
    if( this._num_images > 1 && this.w_lock_scale )
        this.w_lock_scale.style.visibility = "visible"
    // check if image is already loaded -- display if so
    imp = this.imps[path]
    if( imp ) {
        this._current_zoompan = null
        JS9.DisplayImage({display:imp._zoomed_image})
    }
    else {
        this._block_callbacks = true
        this._loading = path
        var from = new RegExp("^.*/")
        var basename = path.replace(from, "")
        this.imps[path] = imp = new JS9pImageProps(this, xsz, ysz, bin, this.zoomsize.x, this.zoomsize.y)
        if( imp.zoomable ) {
            this.setStatus(`Loading ${basename} (downsampled preview), please wait...`)
            this.setStatusRebin("Loading preview...")
            var binopt = average ? `${bin}a` : `${bin}`
            var opts = {fits2fits:true, xcen:(xsz/2>>0), ycen:(ysz/2>>0), xdim:xsz, ydim:ysz, bin:binopt,
                        onload: im => this.onLoadRebin(im, imp),
                        zoom: 'T', zooms: 0,
                        valpos: false}
            this.setDefaultImageOpts(opts)
            JS9.Preload(path, opts, {display:this.disp_rebin});
            this.showPreviewPanel(true)
        } else {
            this.setStatus(`Loading ${basename}, please wait...`)
            this.setStatusRebin('---') // empty text screws up sizes
            var opts = {fits2fits:false,
                        onload: im => this.onLoadNonzoomable(im, imp),
                        zoom: 'T'}
            this.setDefaultImageOpts(opts)
            JS9.Preload(JS9p.imageUrlPrefixNative + path, opts, {display:this.disp_zoom});
            this.showPreviewPanel(false)
        }
    }
}

// _finishLoad()
//      Called when current loading process finishes
//
JS9pPartneredDisplays.prototype._finishLoad = function()
{
    delete this._loading
    if( this._loading_queue.length > 0 ) {
        job = this._loading_queue.shift()
        this.loadImage(job.path, job.xsz, job.ysz, job.bin, job.average)
    }
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

// showPreviewPanel(show)
//      Shows or hides the preview panel
//
JS9pPartneredDisplays.prototype.showPreviewPanel = function(show)
{
    if( this.rebin_div )
        if( show ) {
            this.rebin_div.style.visibility = 'visible'
            this.rebin_div.style.background = this.rebin_div_background
        } else {
            this.rebin_div.style.visibility = 'hidden'
            this.rebin_div.style.background = 'none'
        }
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
JS9pPartneredDisplays.prototype.onLoadRebin = function(im, imp)
{
    JS9p.log("onLoadRebin", im.id, im)
    this.setStatus(`Loaded preview image for ${im.id}`)
    im._js9p = imp
    im._rebinned = true
    imp._rebinned_image = im
    this.current_image[this.disp_rebin] = im
    this.applyScaleColormap(im, imp, true)
    this.applyZoomPan(im, imp)
    imp._user_scale = JS9.GetScale({display:im})
    imp._user_colormap = JS9.GetColormap({display:im})
    this.setStatusRebin("Drag to load new active region")
    imp.updateZoomboxRel(this.zoom_rel)
    imp.zoom_cen = im._zoom_cen = null         // to force an update in checkZoomRegion() callback
    delete this._block_callbacks
    JS9p.log("setting zoombox", imp.zoombox)
    JS9.AddRegions(imp.zoombox, {}, {display:this.disp_rebin})  // this will call checkZoomRegion() callback
}

// onLoadZoom(im, imp)
//      Callback invoked when the zoomed image has been loaded.
//      im is JS9 image (zoomed). imp is an JS9pImageProperties object.
//
JS9pPartneredDisplays.prototype.onLoadZoom = function(im, imp, zoom_cen)
{
    JS9p.log("onLoadZoom", im.id, im, zoom_cen)
    im._js9p = imp
    im._zoomed = true
    im._zoom_cen = zoom_cen
    im._partner_image = imp._rebinned_image
    imp._rebinned_image._partner_image = im
    imp._zoomed_image = im
    this.current_image[this.disp_zoom] = im
    this.applyScaleColormap(im, imp, false)
    this.applyZoomPan(im, imp)
    this.zoom_rel = imp.zoom_rel
    JS9.ChangeRegions("all", imp.zoombox, {display:imp._rebinned_image})
    this.setStatus(`${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} region at ${zoom_cen.x},${zoom_cen.y})`)
    this.setStatusRebin("Drag to load new active region")
    delete this._block_callbacks
    this._finishLoad()
}

// onLoadNonzoomable(im, imp)
//      Callback invoked when a non-zooomable image has been loaded.
//      im is JS9 image (zoomed). imp is an JS9pImageProperties object.
//
JS9pPartneredDisplays.prototype.onLoadNonzoomable = function(im, imp)
{
    JS9p.log("onLoadNonzoomable", im.id, im)
    im._js9p = imp
    im._nonzoom = true
    imp._zoomed_image = im
    this.current_image[this.disp_zoom] = im
    this.applyScaleColormap(im, imp, true)
    this.setStatus(`${im.id} (${imp.size.x}x${imp.size.y})`)
    delete this._block_callbacks
    this._finishLoad()
}

// applyZoomPan(im, imp)
//      Resets the zoom/pan settings of the current image to previously saved ones, if sizes match
//
JS9pPartneredDisplays.prototype.applyZoomPan = function(im, imp)
{
    if( this._current_zoompan && !im._rebinned ) {
        if( this._current_zoompan.imp.size.equals(imp.size) ) {
            zoom = JS9.GetZoom({display:im})
            pan = JS9.GetPan({display:im})
            JS9p.log("applying saved zoom-pan (sizes match)", im.id, this._current_zoompan, zoom, pan)
            if( this._current_zoompan.zoom != zoom )
                JS9.SetZoom(this._current_zoompan.zoom, {display:im})
            if( this._current_zoompan.ox != pan.ox || this._current_zoompan.oy != pan.oy )
                JS9.SetPan(this._current_zoompan.ox, this._current_zoompan.oy, {display:im})
            this._current_zoompan = JS9.GetPan({display:im})
            this._current_zoompan.zoom = JS9.GetZoom({display:im})
        } else {
            JS9p.log("not applying saved zoom-pan (sizes mismatch)")
            this._current_zoompan = null
        }
    }
}


// toggleScaleColormapLock()
//      Toggles the scale-lock property
JS9pPartneredDisplays.prototype.toggleScaleColormapLock = function()
{
    this.lock_scale = !this.lock_scale
    JS9p.log("toggleScaleColormapLock to", this.lock_scale)
    if( this.w_lock_scale )
        if( this.lock_scale )
            this.w_lock_scale.innerHTML = "&#x2612; lock"
        else
            this.w_lock_scale.innerHTML = "&#x2610; lock"
}

// togglePanZoomLock()
//      Toggles the pan-zoom-lock property
JS9pPartneredDisplays.prototype.togglePanZoomLock = function()
{
    this.lock_pan_zoom = !this.lock_pan_zoom
    JS9p.log("togglePanZoomLock to", this.lock_pan_zoom)
    if( this.w_lock_pan_zoom )
        if( this.lock_pan_zoom )
            this.w_lock_pan_zoom.innerHTML = "&#x2612; lock"
        else
            this.w_lock_pan_zoom.innerHTML = "&#x2610; lock"
}

// resetScaleColormap(im)
//    Resets the scale of the current image
JS9pPartneredDisplays.prototype.resetScaleColormap = function()
{
    var im = this.current_image[this.disp_zoom]
    JS9p.log("resetScaleColormap", im)
    if( im == null )
        return
    var cmap = JS9.GetColormap({display: im})
    JS9.SetColormap(cmap.colormap, 1, 0.5, {display: im})
    var scale = JS9.GetScale({display: im})
    JS9.SetScale(scale.scale, im.raw.dmin, im.raw.dmax, {display: im})
}

// checkScaleColormap(im)
//      Checks current scale and colormap, and enables/disables the reset control appropriatelu
JS9pPartneredDisplays.prototype.checkScaleColormap = function(im)
{
    if( this.w_reset_scale ) {
        var cmap = im._colormap || JS9.GetColormap({display:im})
        var scale = im._scale || JS9.GetScale({display:im})
        if(cmap.contrast == 1 && cmap.bias == 0.5 && scale.scalemin == im.raw.dmin && scale.scalemax == im.raw.dmax)
        {
            this.w_reset_scale.disabled = true
            this.w_reset_scale.innerHTML = "&#x21e4;&#x21e5;"
            this.w_reset_scale.title = "The scale limits are currently set to the image min/max values"
//            this.w_reset_scale.innerHTML = "&#x21ce;"
        } else {
            this.w_reset_scale.disabled = false
            this.w_reset_scale.innerHTML = "&#x21a4;&#x21a6;"
            this.w_reset_scale.title = "Click to reset the scale limits to the image min/max values"
//            this.w_reset_scale.innerHTML = "&#x21d4;"
        }
    }
}

// setScaleColormap(im, scale, colormap)
//      Sets the scale and colormap of an image.
JS9pPartneredDisplays.prototype.setScaleColormap = function(im, scale, colormap)
{
    if( scale && !(im._scale === scale))
    {
        JS9.SetScale(scale.scale, scale.scalemin, scale.scalemax, {display: im})
        im._scale = scale
    }
    if( colormap && !(im._colormap === colormap))
    {
        JS9.SetColormap(colormap.colormap, colormap.contrast, colormap.bias, {display: im})
        im._colormap = colormap
    }
    this.checkScaleColormap(im)
}


// applyScaleColormap(im)
//      Sets up the scale and colormap of a loaded image.
//      Ensures that either (a) previous user settings for this image or (b) previous user settings for
//      display overall (if scale-lock is on), or (c) default settings are applied.
//      Called internally from the onLoadXXX() etc. callbacks.
//
JS9pPartneredDisplays.prototype.applyScaleColormap = function(im, imp, use_defaults)
{
    var colormap = imp._user_colormap
    var scale = imp._user_scale
    if( this.lock_scale && this.user_colormap != null ) {
        JS9p.log("setting locked user-defined colormap", this.user_colormap)
        colormap = this.user_colormap
    }
    else if( use_defaults && this.defaults.colormap != null ) {
        JS9p.log("setting default colormap", this.defaults.colormap)
        colormap = { colormap: this.defaults.colormap, contrast: 1, bias: 0.5 }
    }
    if( this.lock_scale && this.user_scale != null ) {
        JS9p.log("setting locked user-defined scale", this.scale)
        scale = this.user_scale
    }
    else if( use_defaults && (this.defaults.scale != null || this.defaults.vmin != null || this.defaults.vmax != null)) {
        JS9p.log("setting default scale", this.scale)
        scale = JS9.GetScale({display: im})
        if( this.defaults.scale != null )
            scale.scale = this.defaults.scale
        if( this.defaults.vmin != null )
            scale.scalemin = this.defaults.vmin
        if( this.defaults.vmax != null )
            scale.scalemax = this.defaults.vmax
    }
    JS9p.log("applying scale", scale, "colormap", colormap)
    this.setScaleColormap(im, scale, colormap)
}

// syncColormap(im)
//      Internal callback for when the colormap of an image is changed. Propagates changes to other display,
//      and saves them for future images.
JS9pPartneredDisplays.prototype.syncColormap = function(im, imp)
{
    this._block_callbacks = true
    this.user_colormap = imp._user_colormap = im._colormap = JS9.GetColormap({display:im})
    if( im._partner_image ) {
        JS9p.log(`  syncing colormap from ${im} to display ${im._partner_image}`)
        this.setScaleColormap(im._partner_image, null, imp._user_colormap)
    }
    else
        this.checkScaleColormap(im)
    delete this._block_callbacks
}

// syncScale(im)
//      Internal callback for when the scale of an image is changed. Propagates changes to other display,
//      and saves them for future images.
JS9pPartneredDisplays.prototype.syncScale = function(im, imp)
{
    this._block_callbacks = true
    this.user_scale = imp._user_scale = im._scale = JS9.GetScale({display:im})
    if( im._partner_image ) {
        JS9p.log(`  syncing scale from ${im} to display ${im._partner_image}`)
        this.setScaleColormap(im._partner_image, imp._user_scale, null)
    }
    else
        this.checkScaleColormap(im)
    delete this._block_callbacks
}

// helper function used by checkZoomRegion() and onImageDisplay() to load new zoomed section
JS9pPartneredDisplays.prototype._updateZoomedSection = function(im, imp, zoom_cen)
{
    JS9.ChangeRegions("all", {movable: false}, {display:imp._rebinned_image})
    this._loading = im.id
    this.current_image[this.disp_zoom] = null
    if( imp._zoomed_image ) {
        JS9.CloseImage({clear:true}, {display: imp._zoomed_image});
        imp._zoomed_image = null
    }
    this.setStatus(`Loading ${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} region at ${zoom_cen.x},${zoom_cen.y}), please wait...`)
    this.setStatusRebin("Loading region...")
    opts = { fits2fits:true,
             xcen: zoom_cen.x,
             ycen: zoom_cen.y,
             xdim: imp.zoomsize.x,
             ydim: imp.zoomsize.y,
             bin:1,
             zoom:'T',
             onload: im => this.onLoadZoom(im, imp, zoom_cen)
         }
    this.setDefaultImageOpts(opts)
    JS9p.log("  preloading", opts)
    JS9.Preload(im.parentFile, opts, {display: this.disp_zoom});
}

// checkZoomRegion(im, xreg)
//      Internal callback for when regions are changed. Checks if the region is the zoombox, and causes
//      a new section of the zoomed image to be loaded if so
//
JS9pPartneredDisplays.prototype.checkZoomRegion = function(im, imp, xreg)
{
    this._block_callbacks = true
    if( im._rebinned && xreg.tags.indexOf("zoombox")>-1 )
    {
        JS9p.log("  zoom-syncing", im, xreg);
        // update the zoom centre
        zoom_cen = imp.updateZoombox(xreg.x*imp.bin, xreg.y*imp.bin)
        JS9.ChangeRegions("all", imp.zoombox, {display:im})
        // check if zoomed image is showing the same centre, update if not
        if( imp._zoomed_image == null || !zoom_cen.equals(imp._zoomed_image._zoom_cen) ) {
            this._current_zoompan = null
            this._updateZoomedSection(im, imp, zoom_cen)
            // wait for onload to clear _block_callbacks, ignore callbacks until then
            return
        }
    }
    delete this._block_callbacks
}


JS9pPartneredDisplays.prototype.onSetZoomPan = function(im, imp)
{
    if( im._zoomed || im._nonzoom ) {
        zoom = JS9.GetZoom({display:im})
        pan = JS9.GetPan({display:im})
        console.log("onSetZoomPan:", im.id, this._current_zoompan, zoom, pan)
        this._current_zoompan = pan
        this._current_zoompan.zoom = zoom
        this._current_zoompan.imp = imp
    }
}

JS9pPartneredDisplays.prototype.onImageDisplay = function(im, imp)
{
    JS9p.log(`  onImageDisplay: ${im.id} on ${im.display.id}: entering`)
    if( this.current_image[im.display.id] === im )
    {
        JS9p.log(`  onImageDisplay: ${im.id} already displayed on ${im.display.id} -- skipping`)
        return
    }
    this._block_callbacks = true
    this.current_image[im.display.id] = im
    // reset scale/colors to locked values, if locked
    this.applyScaleColormap(im, imp, false)
    // if displaying a rebinned image: if a different zoomed image is currently displayed,
    // display the correct one. Delete the guard, since we want the callback to be executed for the zoomed image.
    if( im._rebinned ) {
        zoomed_im = imp._zoomed_image
        if( zoomed_im && !(this.current_image[this.disp_zoom] === zoomed_im) ) {
            delete this._block_callbacks
            JS9.DisplayImage(zoomed_im, {display:this.disp_zoom})
        }
    }
    // if displaying a zoomed image:
    else if( im._zoomed ) {
        JS9p.log("  onImageDisplay zoomed", im)
        this.showPreviewPanel(true)
        if( !(this.current_image[this.disp_rebin] === imp._rebinned_image) ) {
            JS9p.log(`  updating rebinned image ${imp._rebinned_image}`)
            this.current_image[this.disp_rebin] = imp._rebinned_image
            this.applyScaleColormap(imp._rebinned_image, imp, false) // callback will be blocked, so apply it here
            JS9.DisplayImage({display:imp._rebinned_image})
        }
        // set zoom centre of this image based on what we're displaying
        zoom_cen = imp.updateZoomboxRel(this.zoom_rel)
        // if the current section is different, update it
        if( !zoom_cen.equals(im._zoom_cen) )
        {
            JS9.ChangeRegions("all", imp.zoombox, {display:imp._rebinned_image})
            JS9p.log("  changing zoom section")
            this._updateZoomedSection(im, imp, zoom_cen)
            // do not delete _block_callbacks guard -- we'll wait for the onload() callback to do that
            return
        }
        else
        {
            JS9p.log("  updated zoombox", imp.zoombox)
            // if relative section is the same, do nothing, but update the region (note that checkZoomRegion callback will be blocked)
            this.applyZoomPan(im, imp)
            this.setStatus(`${im.id} (${imp.zoomsize.x}x${imp.zoomsize.y} region at ${zoom_cen.x},${zoom_cen.y})`)
        }
    // non-zoomed image displayed: simply set the current image
    } else if( im._nonzoom ) {
        JS9p.log("  onImageDisplay nonzoomed", im)
        this.showPreviewPanel(false)
        this.setStatus(`${im.id} (${imp.size.x}x${imp.size.y})`)
        this.setStatusRebin("---")
    }
    delete this._block_callbacks
    JS9p.log(`  onImageDisplay: ${im.id} on ${im.display.id}: finished`)
}


// JS9p: namespace for partner displays, and associated code
//
var JS9p = {
    // if True, various stuff is logged to console.log()
    debug: true,

    // prepended to image paths (for fits2fits=False loads)
    imageUrlPrefixNative: '',

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
        var imp = im._js9p
        if( imp ) {
            if( imp.partnered_displays._block_callbacks ) {
                JS9p.log(`--blocked ${method}`,im.id,im.display.id,im,args)
            } else {
                JS9p.log(`invoking ${method}`,im.id,im.display.id,im,args)
                imp.partnered_displays[method](im,imp, ...args)
            }
        }
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
                        onsetzoom:              im => JS9p.call_partner_method("onSetZoomPan", im),
                        onsetpan:               im => JS9p.call_partner_method("onSetZoomPan", im),
                        onimagedisplay:         im => JS9p.call_partner_method("onImageDisplay", im),
                        winDims: [0, 0]});

    JS9p.log("registering colormaps")
    if( JS9p_Colormaps )
    {
        for( var name in JS9p_Colormaps )
            JS9.AddColormap(name, JS9p_Colormaps[name], {toplevel:false})
    }
    // JS9.LoadColormap("/static/js9colormaps.json")
})

// onsetpan, onsetzoom, onimagedisplay (im)
//
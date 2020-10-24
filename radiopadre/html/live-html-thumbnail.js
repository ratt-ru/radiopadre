// thanks to https://www.cambus.net/creating-thumbnails-using-systemjs-and-imagemagick/

var page = new WebPage(),
    system = require('system'),
    address, output, size, width, height, timeout;

if (system.args.length < 6) {
    console.log('Usage: live-html-thumbnail.js URL filename width height timeout');
    system.exit();
} else {
    address = system.args[1];
    output = system.args[2];
    width = parseInt(system.args[3]);
    height = parseInt(system.args[4]);
    timeout = parseInt(system.args[5]);

    page.viewportSize = { width: width, height: height };
    page.clipRect = { top: 0, left: 0, width: width, height: height }

    console.log(system.args);
    console.log('opening');
    console.log(address);

    function pageOpenCallback(status) {
        console.log(address, status);
        if (status === 'success') {
            console.log('[SUCCESS] Opened page: ' + address);
            window.setTimeout(function () {
                page.render(output);
                phantom.exit();
            }, timeout);
        } else {
            console.log('[ERROR] Cannot open page: ' + address);
            // DO SOMETHING ON ERROR
            // Close the page and re-create the page - avoid operation canceled error (5)
            console.log('Going to close the page');
            page.close();
            console.log('Going to re-create the page');
            page = require("webpage").create();
            console.log('The page has been re-created!');
        }
    }

    page.open(address, pageOpenCallback);
}
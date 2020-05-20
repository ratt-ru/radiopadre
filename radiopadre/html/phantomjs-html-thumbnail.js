// thanks to https://www.cambus.net/creating-thumbnails-using-systemjs-and-imagemagick/

var page = new WebPage(),
    system = require('system'),
    address, output, size, width, height, timeout;

if (system.args.length < 6) {
    console.log('Usage: phantomjs-html-thumbnail.js URL filename width height timeout');
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

    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('Unable to load the address!');
        } else {
            window.setTimeout(function () {
                page.render(output);
                phantom.exit();
            }, timeout);
        }
    });
}
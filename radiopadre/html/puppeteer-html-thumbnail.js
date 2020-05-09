const puppeteer = require('puppeteer');

args = process.argv.slice(2)

if (args.length < 5) {
    console.log('Usage: node puppeteer-html-thumbnail.js URL filename width height timeout');
    process.exit(1);
}

url = args[0];
output = args[1];
width = parseInt(args[2]);
height = parseInt(args[3]);
delay = parseInt(args[4]);

(async () => {
  const browser = await puppeteer.launch({
     headless: true,
     args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  page.setViewport({width: width, height:height})
  await page.goto(url);
  await page.waitFor(delay);
  await page.screenshot({path: output});

  await browser.close();
})();

// The site's address is xikomu.com. Two older addresses may still serve the same files: the
// Render address (shovl-3upi.onrender.com) and shovll.com (the name until 26 Oct 2026), while
// it's still attached to the site. Anyone who lands on either, from an old link or a search
// result, goes to the same page on xikomu.com instead, and search engines treat the move as a
// redirect. (shovll.com is also meant to be redirected by Cloudflare before it reaches the
// site; this is the fallback.)
// A plain script loaded first in <head> (index.html), so it runs before anything paints, and
// a file rather than inline so the Content-Security-Policy keeps allowing this site's scripts
// only. Sign-ins don't carry over (browsers keep them per address): people sign in again.
(function () {
    var host = window.location.hostname;
    if (/\.onrender\.com$/.test(host) || /(^|\.)shovll\.com$/.test(host)) {
        var here = window.location;
        window.location.replace("https://xikomu.com" + here.pathname + here.search + here.hash);
    }
})();

// The site's address is shovll.com. Its old Render address (shovl-3upi.onrender.com) still
// serves the same files, so anyone who lands there, from an old link or a search result, goes
// to the same page on shovll.com instead, and search engines treat the move as a redirect.
// A plain script loaded first in <head> (index.html), so it runs before anything paints, and
// a file rather than inline so the Content-Security-Policy keeps allowing this site's scripts
// only. Sign-ins don't carry over (browsers keep them per address): people sign in again.
(function () {
    if (/\.onrender\.com$/.test(window.location.hostname)) {
        var here = window.location;
        window.location.replace("https://shovll.com" + here.pathname + here.search + here.hash);
    }
})();

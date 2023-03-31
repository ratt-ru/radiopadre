
document.radiopadre_layouts = {}

// adds a section to the list and repopulate all bookmark bars
document.radiopadre_layouts.add_section = function() {
    var layouts = document.radiopadre_layouts
    layouts.section_labels = [];
    layouts.section_names = {};
    var bookmark_bars = document.getElementsByClassName("rp-section-bookmarks");
    // console.log("bookmarks are ", bookmark_bars)
    var bar0;
    for(bar0 of bookmark_bars) {
        var label = bar0.getAttribute("data-label");
        if( !layouts.section_labels.includes(label) ) {
            layouts.section_labels.push(label);
            layouts.section_names[label] = bar0.getAttribute("data-name");
        }
    }
    // loop over all bookmark bars in document
    for(bar0 of bookmark_bars) {
        var label0 = bar0.getAttribute("data-label");
        // clear content
        var bar = bar0.cloneNode(false);  /* kills children */
        bar0.parentNode.replaceChild(bar, bar0);
        var label;
        // reinsert content
        for(label of layouts.section_labels) {
            var element;
            // content is a link or a simple text element
            if( label == label0 ) {
                element = document.createElement('div');
                element.className = "rp-active-section";
            } else {
                element = document.createElement('a');
                element.className = "rp-section-link";
                element.href = "#" + label;
            }
            element.innerHTML = layouts.section_names[label];
            bar.appendChild(element);
        }
    }
    return layouts.section_labels;
}


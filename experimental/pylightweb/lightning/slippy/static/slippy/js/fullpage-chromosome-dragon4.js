
function bindOneToolTip(textIDString, overlayIDString) {
    var tip = jQuery(textIDString);
    //console.log(tip);
    //console.log(jQuery(overlayIDString));
    jQuery(overlayIDString).hover(function (e) {
        var mousex = e.pageX + 20, //Get X coodrinates
            mousey = e.pageY + 20, //Get Y coordinates
            tipWidth = tip.width(), //Find width of tooltip
            tipHeight = tip.height(), //Find height of tooltip
        //Distance of element from the right edge of viewport
            tipVisX = $(window).width() - (mousex + tipWidth),
        //Distance of element from the bottom of viewport
            tipVisY = $(window).height() - (mousey + tipHeight);
        if (tipVisX < 20) { //If tooltip exceeds the X coordinate of viewport
            mousex = e.pageX - tipWidth - 20;
        }
        if (tipVisY < 20) { //If tooltip exceeds the Y coordinate of viewport
            mousey = e.pageY - tipHeight - 20;
        }
        tip.css({top: mousey, left: mousex, position: 'absolute'});
        tip.show().css({opacity: 0.8}); //Show tooltip
    }, function () {
        tip.hide(); //Hide tooltip
    });
}

// getOffsets requests tile offsets file and put data into array.
// NOTE: the format of this file might change in the future.
function getOffsets() {
    var offsets = [];
    $.ajax({
        url: "{% static 'slippy/tile_offsets.txt' %}",
        success: function (data) {
            offsets = data.split(",");
        },
        async: false
    });
    return offsets;
}

function beginDragon(datafile1) {
    d3.csv(datafile1, function (error, data) {
        tilePixelSize = 15 * 2;
        borderPixelSize = 2;

        var offsets = getOffsets();
//        console.log(offsets)
        var annotations = [];
        var yposition = 0;
        var idx = 0;
        data.forEach(function (d) {
            var idname = d.name.replace(/\./g, '');
            var longtext = '<div id="Text'.concat(idname, '" style="display:none;width:250px;background-color:#fff;"><p>Supertile ', d.name, ' has ', d.num, ' tiles</p></div>');
            jQuery("#overlaytexts").append(longtext);
            //console.log(yposition);
            annotations.push({
                id: idname,
                px: 0,
                py: yposition,
                width: tilePixelSize,
                height: tilePixelSize,
                className: 'highlight'
            });
            yposition = (tilePixelSize + borderPixelSize) * parseInt(offsets[idx]);
            idx++;
        });
        console.log(yposition);
        //var chr = $("#chrPicker").val();
        var srcString = "/slippy/static/slippy/pngs/entire.dzi";
        viewer = OpenSeadragon({
            id: "contentDiv",
            prefixUrl: "/slippy/static/slippy/js/openseadragon-images/",
            tileSources: srcString,
            visibilityRatio: 0.7,
            showNavigator: true,
            navigatorPosition: 'BOTTOM_LEFT',
            navigatorHeight: 400,
            navigatorWidth: 80,
            //debugMode: true,
            toolbar: "toolbarDiv",
            overlays: annotations
        });

        //Begins an OpenSeadragon.Viewer
        //Adding url hyperlinks would be useful
        //Annotation of genes, etc

        imagingHelper = viewer.activateImagingHelper({});
        viewerInputHook = viewer.addViewerInputHook({hooks: [
            {tracker: 'viewer', handler: 'clickHandler', hookHandler: onViewerClick}
        ]});
        function onViewerClick(event) {
            //	event.preventDefaultAction = true;
        }

        jQuery(function () {
            //Tooltips
            setTimeout(function panAndZoomToOrigin() {
                viewer.viewport.zoomTo(viewer.viewport.getMaxZoom());
                //console.log(imagingHelper.imgWidth);
                //console.log(imagingHelper.imgHeight);
                viewer.viewport.panTo(new OpenSeadragon.Point(0, 0));
            }, 1000);
            setTimeout(bindtooltip, 2000);
        });

        function bindtooltip() {
            annotations.forEach(function (entry) {
                bindOneToolTip("#Text" + entry.id, "#" + entry.id);
            });
        }
    });
}

jQuery(document).ready(function () {
    var tools = jQuery("#toolbarDiv"),
        content = jQuery("#contentDiv"),
        h = jQuery(window).height();
//	tools.css("width", w);
    tools.css("height", 35);
//	content.css("width", w);
    content.css("height", h - 110); //hardcode 120px to accomidate toolbar and navbar
    beginDragon("/slippy/static/slippy/TileNumSupertiles.csv");
//	var w = jQuery(".main").width(),

});

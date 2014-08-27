function bindOneToolTip(textIDString, overlayIDString) {
	var tip = jQuery(textIDString);
	jQuery(overlayIDString).hover(function (e) {
		var mousex = e.pageX + 20, //Get X coodrinates
			mousey = e.pageY + 20, //Get Y coordinates
    	    tipWidth = tip.width(), //Find width of tooltip
    	    tipHeight = tip.height(), //Find height of tooltip
    	    tipVisX = $(window).width() - (mousex + tipWidth), //Distance of element from the right edge of viewport
    	    tipVisY = $(window).height() - (mousey + tipHeight); //Distance of element from the bottom of viewport
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
// getOffsets accepts the tile offsets file and puts the data into array.
// NOTE: the format of this file might change in the future

function getOffsets(urlString) {
	var offsets = [];
	$.ajax({
		url: urlString,
		success: function (data) {
			offsets = data.split(",");
		},
		async: false
	});
	return offsets;
}

function beginDragon(datafile1, tilePixelSize, borderPixelSize, offsetURL, srcString, prefixString) {
    d3.csv(datafile1, function (error, data) {
        var offsets = getOffsets(offsetURL);
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
            yposition += (tilePixelSize + borderPixelSize) * parseInt(offsets[idx]);
            idx++;
        });
        //console.log(yposition);
        //var chr = $("#chrPicker").val();
        viewer = OpenSeadragon({
            id: "contentDiv",
            prefixUrl: prefixString,
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
            /*setTimeout(function panAndZoomToOrigin() {
                viewer.viewport.zoomTo(viewer.viewport.getMaxZoom());
                //console.log(imagingHelper.imgWidth);
                //console.log(imagingHelper.imgHeight);
                viewer.viewport.panTo(new OpenSeadragon.Point(0, 0));
            }, 1000);*/
            setTimeout(bindtooltip, 2000);
        });
        function bindtooltip() {
            annotations.forEach(function (entry) {
                bindOneToolTip("#Text" + entry.id, "#" + entry.id);
            });
        }
    });
}

function addGeneAnnoation(gene, spath, sstep, epath, estep, tilePixelSize, borderPixelSize, offsetStr) {
	console.log(gene);
	var offsets = getOffsets(offsetStr),
		beginstep = sstep % 8000,
		beginoffset = Math.floor(sstep/8000),
		endstep = estep % 8000,
		endoffset = Math.floor(estep/8000),
		startpath = parseInt(offsets[spath]),
		endpath = parseInt(offsets[epath]);
	if (beginoffset == endoffset && startpath == endpath) {
		console.log(beginstep);
		console.log(endstep);
		console.log(startpath);
		beginstepcoor = beginstep*(tilePixelSize+borderPixelSize) - borderPixelSize;
		endstepcoor = endstep*(tilePixelSize+borderPixelSize) - borderPixelSize;
		pathcoor = (startpath+beginoffset)*(tilePixelSize+borderPixelSize) - borderPixelSize;
		console.log(pathcoor);		
		console.log(beginstepcoor);
		console.log(endstepcoor);
		//Write mouseover text object
		var textToAppend = '<div id="Text'.concat(gene, '" style="display:none;width:250px;background-color:#fff;"><p>', gene, ' Gene.</p></div>');
		jQuery('#overlaytexts').append(textToAppend);
		viewer.addOverlay({
			id: gene,
			px: beginstepcoor,
			py: pathcoor,
			width: endstepcoor-beginstepcoor,
			height: tilePixelSize,
			className: 'highlight'
		});
		setTimeout(function() {
			bindOneToolTip("#Text".concat(gene), "#".concat(gene));
		}, 2000);
		var genePos = new OpenSeadragon.Point(beginstepcoor + (endstep - beginstep) * (tilePixelSize+borderPixelSize) / 2, pathcoor);
		genePos = imagingHelper.dataToLogicalPoint(genePos);
		imagingHelper.centerAboutLogicalPoint(genePos);
	}
}


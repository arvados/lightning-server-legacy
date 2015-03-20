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
		tip.css({top: mousey, left: mousex, position: 'absolute', 'z-index': 1});
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
//TODO: don't need offsetURL anymore
function beginDragon(datafile1, tilePixelSize, borderPixelSize, offsetURL, srcString, prefixString, offsetIterURL) {
    d3.csv(datafile1, function (error, data) {
        viewer = OpenSeadragon({
            id: "contentDiv",
            prefixUrl: prefixString,
            tileSources: srcString,
            visibilityRatio: 0.8,
            showNavigator: true,
            navigatorPosition: 'BOTTOM_LEFT',
            navigatorHeight: 400,
            navigatorWidth: 80,
            //debugMode: true,
            //toolbar: "toolbarDiv",
            //overlays: annotations
        });
        //Begins an OpenSeadragon.Viewer
        //Adding url hyperlinks would be useful
        //Annotation of genes, etc
        imagingHelper = viewer.activateImagingHelper({});
        viewerInputHook = viewer.addViewerInputHook({hooks: [
            {tracker: 'viewer', handler: 'clickHandler', hookHandler: onViewerClick}
        ]});
        function onViewerClick(event) {
            event.preventDefaultAction = true;
			var poss_overlays = jQuery('.annotation');
			for (var i = 0; i < poss_overlays.length; i++){
				id = poss_overlays[i].id;
				if (jQuery('#'+id+':hover').length > 0){
					links = jQuery('#Text'+id).find('a');
					for (var j = 0; j < links.length; j++){
						links[j].click();
					}
				}
			}
			var offsets = getOffsets(offsetIterURL);
			var viewportPoint = viewer.viewport.pointFromPixel(event.position);
  			var imagePoint = viewer.viewport.viewportToImageCoordinates(viewportPoint.x, viewportPoint.y);
			var step = Math.floor((imagePoint.x + borderPixelSize)/(tilePixelSize+borderPixelSize));
			var y = Math.floor((imagePoint.y + borderPixelSize)/(tilePixelSize+borderPixelSize));
			if (step >= 0 && y >= 0){
				var path = 0;
				var path_y = offsets[path];
				while (path_y < y){
					path ++;
					path_y = offsets[path];
				}
				if (path_y != y){
					path --;
					step += map_width*(y - offsets[path]);
				}
				console.log(step, path);
			}
        }
        /*jQuery(function () {
            //Tooltips
            setTimeout(function panAndZoomToOrigin() {
                viewer.viewport.zoomTo(viewer.viewport.getMaxZoom());
                //console.log(imagingHelper.imgWidth);
                //console.log(imagingHelper.imgHeight);
                viewer.viewport.panTo(new OpenSeadragon.Point(0, 0));
            }, 1000);
        });*/
    });
}

//TODO: add zoom option
function addGeneAnnotation(gene, spath, sstep, epath, estep, tilePixelSize, borderPixelSize, offsetStr, panTo, urlArray) {	
	//console.log(gene, spath, sstep, epath, estep, tilePixelSize, borderPixelSize, offsetStr, panTo);
	var offsets = getOffsets(offsetStr),
		overlayid = '#'.concat(gene),
		overlayidpartial = '#'.concat(gene, 'part1'),
		beginstep = sstep % map_width,
		beginoffset = Math.floor(sstep/map_width),
		endstep = estep % map_width,
		endoffset = Math.floor(estep/map_width),
		startpath = parseInt(offsets[spath]),
		endpath = parseInt(offsets[epath]),
		beginstepcoor = beginstep*(tilePixelSize+borderPixelSize) - borderPixelSize,
		endstepcoor = endstep*(tilePixelSize+borderPixelSize) - borderPixelSize,
		beginpathcoor = (startpath+beginoffset)*(tilePixelSize+borderPixelSize) - borderPixelSize,
		endpathcoor = (endpath+endoffset)*(tilePixelSize+borderPixelSize) - borderPixelSize,
		genePos;

	if (beginoffset == endoffset && startpath == endpath) {
		genePos = new OpenSeadragon.Point(beginstepcoor + (endstep - beginstep) * (tilePixelSize+borderPixelSize) / 2, endpathcoor);
	} else {
		genePos = new OpenSeadragon.Point(0, endpathcoor);
	}
	//Only add the annotation if it's not already there
	if (jQuery(overlayid).length == 0 && jQuery(overlayidpartial).length == 0) {
		var links,
			href = '';
		if (urlArray[0] != ""){
			if (urlArray.length > 1){
				links = ' has GeneReview articles associated with it. Click to visit all of them.'
			} else {
				links = ' has a GeneReview article associated with it. Click to visit.'
			}
			for (var i = 0; i < urlArray.length; i++) {
				var article_num = i+1;
				href += '<a href="' + urlArray[i] + '" target="_blank"></a>';
			}
		} else {
			links = '';	
		}
		if (beginoffset == endoffset && startpath == endpath) {
			//Write mouseover text object
			var textToAppend = '<div id="Text'.concat(gene, '" style="display:none;width:250px;background-color:#fff;">', href, '<p>', gene, links, '</p></div>');
			jQuery('#overlaytexts').append(textToAppend);
			viewer.addOverlay({
				id: gene,
				px: beginstepcoor,
				py: beginpathcoor,
				width: endstepcoor+tilePixelSize-beginstepcoor,
				height: tilePixelSize,
				className: 'highlight annotation'
			});
			setTimeout(function() {
				bindOneToolTip("#Text".concat(gene), "#".concat(gene));
			}, 200);
		} else {
			//This assumes nothing crosses more than one cutoff
			var textToAppend = '<div id="Text'.concat(gene, 'part1" style="display:none;width:250px;background-color:#fff;">', href, '<p>', gene, ' (part 1)', links, '</p></div><div id="Text', gene, 'part2" style="display:none;width:250px;background-color:#fff;">', href, '<p>', gene, ' (part 2)', links, '</p></div>');
			jQuery('#overlaytexts').append(textToAppend);
			viewer.addOverlay({
				id: gene.concat("part1"),
				px: beginstepcoor,
				py: beginpathcoor,
				width: ((map_width-1)*(tilePixelSize+borderPixelSize) - borderPixelSize) +tilePixelSize-beginstepcoor,
				height: tilePixelSize,
				className: 'highlight broken annotation'
			});
			viewer.addOverlay({
				id: gene.concat("part2"),
				px: 0,
				py: endpathcoor,
				width: endstepcoor+tilePixelSize,
				height: tilePixelSize,
				className: 'highlight broken annotation'
			});
			setTimeout(function() {
				bindOneToolTip('#Text'.concat(gene, 'part1'), '#'.concat(gene, 'part1'));
				bindOneToolTip('#Text'.concat(gene, 'part2'), '#'.concat(gene, 'part2'));
			}, 200);	
		}
	} else {
		console.log("Found a copy", overlayid, overlayidpartial);
	}
	if (panTo) {
		genePos = imagingHelper.dataToLogicalPoint(genePos);
		imagingHelper.centerAboutLogicalPoint(genePos);
		viewer.viewport.zoomTo(viewer.viewport.getMaxZoom());
	}
}
lpad = function(value, padding) {
    var zeroes = "0";
    for (var i = 0; i < padding; i++) { zeroes += "0"; }
    return (zeroes + value).slice(padding * -1);
};
getTileCoor = function(CGF) {
	strTilename = CGF.toString(16);
	strTilename = lpad(strTilename, 9);
	path = parseInt(strTilename.slice(0,3), 16);
	version = parseInt(strTilename.slice(3,5), 16);
	step = parseInt(strTilename.slice(5), 16)
	return [path, version, step];
};

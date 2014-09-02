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

function beginDragon(datafile1, tilePixelSize, borderPixelSize, offsetURL, srcString, prefixString, offsetIterURL) {
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
            event.preventDefaultAction = true;
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
					step += 8000*(y - offsets[path]);
				}
				console.log(step, path);
			}
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

function addGeneAnnotation(gene, spath, sstep, epath, estep, tilePixelSize, borderPixelSize, offsetStr) {
	//console.log(gene);
	var offsets = getOffsets(offsetStr),
		beginstep = sstep % 8000,
		beginoffset = Math.floor(sstep/8000),
		endstep = estep % 8000,
		endoffset = Math.floor(estep/8000),
		startpath = parseInt(offsets[spath]),
		endpath = parseInt(offsets[epath]);
	if (beginoffset == endoffset && startpath == endpath) {
		//console.log(beginstep);
		//console.log(endstep);
		//console.log(spath);
		//console.log(beginoffset);

		beginstepcoor = beginstep*(tilePixelSize+borderPixelSize) - borderPixelSize;
		endstepcoor = endstep*(tilePixelSize+borderPixelSize) - borderPixelSize;
		pathcoor = (startpath+beginoffset)*(tilePixelSize+borderPixelSize) - borderPixelSize;

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

function addAllGenes(geneArray, tilePixelSize, borderPixelSize, offsetStr){
	var lpad = function(value, padding) {
    	var zeroes = "0";
    	for (var i = 0; i < padding; i++) { zeroes += "0"; }
    	return (zeroes + value).slice(padding * -1);
	};
	var getTileCoor = function(CGF) {
		strTilename = CGF.toString(16);
		strTilename = lpad(strTilename, 9);
		path = parseInt(strTilename.slice(0,3), 16);
		version = parseInt(strTilename.slice(3,5), 16);
		step = parseInt(strTilename.slice(5), 16)
		return [path, version, step];
	};
	var annotations = [];
	var textToAppend = '';
	geneArray.forEach(function (g) {
		console.log(g);
		var	startCoor = getTileCoor(g.startCGF),
			endCoor = getTileCoor(g.endCGF),
			offsets = getOffsets(offsetStr),
			beginstep = parseInt(startCoor[2]) % 8000,
			beginoffset = Math.floor(parseInt(startCoor[2])/8000),
			endstep = parseInt(endCoor[2]) % 8000,
			endoffset = Math.floor(parseInt(endCoor[2])/8000),
			startpath = parseInt(offsets[startCoor[0]]),
			endpath = parseInt(offsets[endCoor[0]]),
			gene = g.geneName;
		if (beginoffset == endoffset && startpath == endpath) {
			beginstepcoor = beginstep*(tilePixelSize+borderPixelSize) - borderPixelSize;
			endstepcoor = endstep*(tilePixelSize+borderPixelSize) - borderPixelSize;
			pathcoor = (startpath+beginoffset)*(tilePixelSize+borderPixelSize) - borderPixelSize;
			annotations.push(gene);
			textToAppend += '<div id="Text'.concat(gene, '" style="display:none;width:250px;background-color:#fff;"><p>', gene, ' Gene.</p></div>');
			viewer.addOverlay({
				id: gene,
				px: beginstepcoor,
				py: pathcoor,
				width: endstepcoor-beginstepcoor,
				height: tilePixelSize,
				className: 'highlight'
			});
		}
	});
	jQuery('#overlaytexts').append(textToAppend);
	jQuery(function () {
		setTimeout(bindtooltip, 2000);
	});
	function bindtooltip() {
		annotations.forEach(function (gene) {
			bindOneToolTip("#Text".concat(gene), "#".concat(gene));
		});
	}
}

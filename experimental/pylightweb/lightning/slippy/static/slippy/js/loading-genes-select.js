function loadGenesWithProgress(iterTextString, loadAllURL){
	var xhr,
		keepAddingOverlays,
		genesToDisplay,
		max_val,
		i,
		loadGenesSelection = jQuery("#filter").selectmenu({width:400, select: function(event) {
			var filterName = jQuery("#filter").val();
			if (filterName != ""){
				var keepGoing = confirm("Warning, loading multiple genes takes time. Continue?");
				if (keepGoing){
					dialog.dialog( "open" );
				}
			}
			else {
				alert("Select a group of genes");
			}}})
			.selectmenu("menuWidget")
				.addClass("overflow");
		function closeDownload() {
			xhr.abort();
			keepAddingOverlays = false;
			dialog
				.dialog( "option", "buttons", dialogButtons )
				.dialog( "close" );
			progressbar.progressbar( "value", false );
			progressLabel
				.text( "Finding Genes..." );
		}
		function displayOneGene() { 
			if (genesToDisplay.length != 0) {
				gene = genesToDisplay.pop();
				i ++;
				if (gene != ""){
					prop = gene.split(',');
					startcoor = getTileCoor(parseInt(prop[1]));
					endcoor = getTileCoor(parseInt(prop[2]));	
					addGeneAnnotation(prop[0],startcoor[0],startcoor[2],endcoor[0],endcoor[2],tilePixelSize, borderPixelSize, iterTextString, false);
				}
				if (keepAddingOverlays){
					progressbar.progressbar( "value", Math.ceil((i/max_val)*100) );
					setTimeout(displayOneGene,10);
				}
			}
		}
		function startDisplayingGenes(res, status) {
			progressbar.progressbar( "value", 0);
			if (status == "success"){
				genesToDisplay = res.responseText.replace(/\s/g, '').split(';');
				max_val = genesToDisplay.length;
				keepAddingOverlays = true;
				i = 0;
				setTimeout(displayOneGene,10);
			} else {
				alert(res.responseText);
			}
		}
		var progressbar = jQuery("#progressbar"),
			progressLabel = jQuery(".progress-label");
		progressbar.progressbar({
			value: false,
			change: function() {
				progressLabel.text( "Current Progress: " + progressbar.progressbar( "value" ) + "%" );
			},
			complete: function() {
				progressLabel.text( "Complete!" );
				dialog.dialog( "option", "buttons", [{
					text: "Close",
					click: closeDownload
				}]);
				jQuery(".ui-dialog button").last().focus();
			}
		});
		var dialogButtons = [{
				text: "Cancel Gene Load",
				click: closeDownload
			}],
			dialog = jQuery("#gene-load-dialog").dialog({
				autoOpen: false,
				closeOnEscape: false,
				resizable: false,
				buttons: dialogButtons,
				open: function() {
					var name = jQuery("#filter").val();
					var args = { type:"GET", url:loadAllURL, data:{filter:name}, complete:startDisplayingGenes };
					xhr = jQuery.ajax(args);
				},
			});
}

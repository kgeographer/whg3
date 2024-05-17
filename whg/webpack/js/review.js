// /whg/webpack/js/review.js

import { mappy, layersets, initialiseMap, addReviewListeners } from './review-common';
import './notes.js';

import '../css/review.css';


function waitMapLoad() {
    return new Promise((resolve) => {
        mappy.on('load', () => {
			initialiseMap();
			resolve();
        });
    });
}

function waitDocumentReady() {
    return new Promise((resolve) => {
        $(document).ready(() => resolve());
    });
}

function toggleGeonamesReview() {
	$('#geonames_review').toggle();
}

Promise.all([waitMapLoad(), waitDocumentReady()])
    .then(() => {

    if ($('.wdlocal').length > 0) {
		// hide geonames (gn) initially if any wdlocal records
        $('.gn').hide();
        // $('#toggle_geonames_review').show();
        $('.show-link').show();
    } else {
		// show geonames (gn) initially if no wdlocal records
        $('.gn').show();
        // $('#toggle_geonames_review').hide();
        $('.show-link').hide();
    }

    $('#toggle_geonames_review').on('click', function(e) {
        e.preventDefault(); // prevent the default action

        // toggle visibility of .auth-match and adjacent .matchbar elements associated with 'gn'
        $('.auth-match').each(function() {
            if ($(this).find('a[data-auth="gn"]').length > 0) {
                $(this).prev('.matchbar').toggle();
                $(this).toggle();
            }
        });
        
        // toggle visibility of geonames map markers
        if (!!layersets['geonames']) layersets['geonames'].toggleVisibility();

        // change the text of the link
        $(this).text(function(i, text){
            return text === "Show GeoNames hits" ? "Hide GeoNames hits" : "Show GeoNames hits";
        })
    });

		if (page_variant == 'reconciliation') {

			console.log(`already: ${ already }`)
			if (already !=='') {
				alert('last record was saved by someone else, this is the next')
			}
		
			$(".view-comments").click(function() {
				$(".record_notes").toggle(300)
			})
			
		}
		
		else if (page_variant == 'accession') {
		
			let placeid = $('script').filter(function() { // TODO: Redundant code?
				return this.id.match("placeid")
			}).text();
			
			if (test == "on") {
				$("#review_nav").css("background-color", "lightsalmon");
				$("input:radio").attr("disabled", "disabled");
				$("#btn_save").hide();
				$("#defer_link").hide();
			}
		
			var dspop = $(".pop-dataset").popover({
				trigger: 'focus',
				placement: 'right',
				html: true
			}).on('show.bs.popover', function() {
				$.ajax({
					url: '/api/datasets/',
					data: {
						label: $(this).data('label')
					},
					dataType: "JSON",
					async: false,
					success: function(data) {
						let ds = data.results[0]
						//console.log('ds',ds)
						let html = '<p class="thin"><b>Title</b>: ' + ds.title + '</p>'
						html += '<p class="thin"><b>Description</b>: ' + ds.description + '</p>'
						html += '<p class="thin"><b>WHG Owner</b>: ' + ds.owner + '</p>'
						html += '<p class="thin"><b>Creator</b>: ' + ds.creator + '</p>'
						dspop.attr('data-content', html);
					}
				});
			});
			
		}
		
		addReviewListeners();	
		
    })
    .catch(error => console.error("An error occurred:", error));

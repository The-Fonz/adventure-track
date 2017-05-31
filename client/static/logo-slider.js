$(document).ready(function(){
			$('.logos').slick({
                variableWidth: true,
                infinite: true,
				slidesToShow: 1,
				slidesToScroll: 1,
				autoplay: true,
				autoplaySpeed: 3000,
                speed: 1500,
				arrows: false,
				dots: false,
                pauseOnHover: false,
                centerMode: true,
                // responsive: [{
				// 	breakpoint: 768,
				// 	settings: {
				// 		slidesToShow: 3
				// 	}
				// }, {
				// 	breakpoint: 520,
				// 	settings: {
				// 		slidesToShow: 2
				// 	}
				// }]
			});
		});
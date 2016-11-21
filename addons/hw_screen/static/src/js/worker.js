    $().ready(function() {
        (function worker() {
            var base = $('head base')[0];
            $.ajax({
                type: 'GET',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',
                    success: function(data) {
                        var parsedHTML = $('.wrap').html($.parseHTML(data.rendered_html));
                        console.log(parsedHTML);

                        
                    },

                    complete: function() {
                        setTimeout(worker, 1000);
                    }
            });
        })();
    });
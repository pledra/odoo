    $().ready(function() {
        (function worker() {
            var base = $('head base')[0];
            $.ajax({
                type: 'GET',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',
                    success: function(data) {
                        var parsedHTML = $('head').html($.parseHTML(data.rendered_html));
                        var pos_display_contents = parsedHTML.find('.container-fluid').detach();
                        $('.wrap').html(pos_display_contents);                        
                    },

                    complete: function() {
                        setTimeout(worker, 1000);
                    }
            });
        })();
    });
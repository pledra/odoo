    $().ready(function() {
        (function worker() {
            $.ajax({
                type: 'GET',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',

                success: function(data) {
                    var parsedHTML = $('.wrap').html($.parseHTML(data.rendered_html));                        
                },

                complete: function(jqXHR,err) {
                    worker();
                },

                timeout: 30000,
            });
        })();
    });
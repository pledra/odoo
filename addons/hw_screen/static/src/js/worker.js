    $().ready(function() {
        var mergedHead = false;

        (function worker() {
            $.ajax({
                type: 'GET',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',

                success: function(data) {
                    var trimmed = $.trim(data.rendered_html);
                    var parsedHTML = $('.shadow').html($.parseHTML(trimmed,true));
                    if (!mergedHead) {
                        mergedHead = true;
                        $("head").append($(".resources",parsedHTML).html());
                    }
                    
                    $(".resources",parsedHTML).remove();
                    $(".wrap").html(parsedHTML.html());
                    $(".shadow").html("");                    
                },

                complete: function(jqXHR,err) {
                    worker();
                },

                timeout: 30000,
            });
        })();
    });
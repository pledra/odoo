    $().ready(function() {
        (function worker() {
            $.ajax({
                type: 'GET',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',

                success: function(data) {
                    var mergedHead = false;

                    var parsedHTML = $('.shadow').html($.parseHTML(data.rendered_html));
                    if (!mergedHead) {
                        mergedHead = true;
                        $("head").append(parsedHTML.$(".resources"));
                    }
                    parsedHTML.$(".resources").remove();
                    $(".wrap").html(parsedHTML);
                    $(".shadow").html("");                    
                },

                complete: function(jqXHR,err) {
                    worker();
                },

                timeout: 30000,
            });
        })();
    });
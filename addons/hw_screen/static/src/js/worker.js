    $(function() {
        var mergedHead = false;
        var current_client_url = "";

        function longpolling() {
            $.ajax({
                type: 'POST',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',
                beforeSend: function(xhr){xhr.setRequestHeader('Content-Type', 'application/json');},
                data: JSON.stringify({jsonrpc: '2.0'}),

                success: function(data) {
                    var trimmed = $.trim(data.result.rendered_html);
                    var parsedHTML = $('.shadow').html($.parseHTML(trimmed,true));
                    var new_client_url = $(".resources > base",parsedHTML).attr('href');

                    if (!mergedHead || (current_client_url !== new_client_url)) {

                        mergedHead = true;
                        current_client_url = new_client_url;
                        $("body").css("color", 'black');
                        $("head").children().not('.origin').remove();
                        $("head").append($(".resources",parsedHTML).html());
                    } 

                    $(".resources",parsedHTML).remove();
                    $(".container").html($('.pos-customer_facing_display', parsedHTML).html());
                    $(".shadow").html("");              
                },

                complete: function(jqXHR,err) {
                    longpolling();
                },

                timeout: 30000,
            });
        };

        longpolling();
    });
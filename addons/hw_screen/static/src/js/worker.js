    $().ready(function() {
        var mergedHead = false;

        (function longpolling() {
            $.ajax({
                type: 'POST',
                url: 'http://'+window.location.host+'/point_of_sale/get_serialized_order',
                dataType: 'json',
                beforeSend: function(xhr){xhr.setRequestHeader('Content-Type', 'application/json');},
                data: JSON.stringify({jsonrpc: '2.0'}),

                success: function(data) {
                    var trimmed = $.trim(data.result.rendered_html);
                    var parsedHTML = $('.shadow').html($.parseHTML(trimmed,true));
                    if (!mergedHead) {
                        mergedHead = true;
                        $("head").append($(".resources",parsedHTML).html());
                    }

                    var current_client_ip = $("head > base");
                    
                    $(".resources",parsedHTML).remove();
                    $(".wrap").html(parsedHTML.html());
                    $(".shadow").html("");                    
                },

                complete: function(jqXHR,err) {
                    longpolling();
                },

                timeout: 30000,
            });
        })();
    });
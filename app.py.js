$(document).ajaxSuccess(function(event, xhr, opt) {

    if (opt.url.indexOf('ajax/bid') === -1) {
        return;
    }

    var playlist = JSON.parse(xhr.responseJSON.aItems);

    // Title + Long text description
    var description = [
        $('.ls-topic-header h1').text().trim(),
        "\n",
        $('.ls-topic-content').text().trim(),
        "\n\n",
        // Extract metadata: Author / Length / ...
        $('.book-info [class="panel-item"] > *:not(.voting-item):not(.fa)')
            .text(function(k, v) { return v.trim() + "\n"; })
            .text()
            .replace(/:\s+/g, ": ")
            .replace(/\n\(/g, " (")
            .trim(),
        "Жанр: " + $('.books-block-header a:last').text().replace(/[«»]/g, ''),
        "\n",
        "Источник: " + document.location.href,
        "\n",
    ];

    var data = {
        description: description.join("\n"),
        cover: $('.picture-side img:last').attr('src'),
        playlist: playlist,
    };

    $('body').html($('<div />', {
        id: 'book_data',
        text: JSON.stringify(data),
    }));

});

var book_id = $('[data-global-id]').attr('data-global-id');
$(document).audioPlayer(book_id, 0);


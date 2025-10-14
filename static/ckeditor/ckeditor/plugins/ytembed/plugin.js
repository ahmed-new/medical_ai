CKEDITOR.plugins.add('ytembed', {
  icons: 'ytembed',
  init: function(editor) {
    function extractId(url) {
      if (!url) return null;
      var m;
      // https://www.youtube.com/watch?v=VIDEOID
      m = url.match(/[?&]v=([^&#]+)/); if (m) return m[1];
      // https://youtu.be/VIDEOID
      m = url.match(/youtu\.be\/([^?&#/]+)/); if (m) return m[1];
      // https://www.youtube.com/embed/VIDEOID
      m = url.match(/youtube\.com\/embed\/([^?&#/]+)/); if (m) return m[1];
      // shorts
      m = url.match(/youtube\.com\/shorts\/([^?&#/]+)/); if (m) return m[1];
      return null;
    }

    editor.addCommand('insertYouTube', {
      exec: function(ed) {
        var url = prompt('Paste YouTube URL:');
        if (!url) return;
        var vid = extractId(url);
        if (!vid) { alert('Cannot detect video id.'); return; }
        var html = '<div class="yt-embed" contenteditable="false" style="max-width:100%;position:relative;padding-bottom:56.25%;height:0;overflow:hidden;">'
          + '<iframe src="https://www.youtube.com/embed/' + vid + '" '
          + 'style="position:absolute;top:0;left:0;width:100%;height:100%;" '
          + 'frameborder="0" allowfullscreen></iframe></div>';
        ed.insertHtml(html);
      }
    });

    editor.ui.addButton('YouTube', {
      label: 'Insert YouTube',
      command: 'insertYouTube',
      toolbar: 'insert',
      icon: 'https://img.icons8.com/ios-filled/50/youtube-play.png' // اختياري
    });
  }
});

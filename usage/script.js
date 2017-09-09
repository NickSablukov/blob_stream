function fail(str) {
    alert(str);
}

var output_console = document.getElementById('output_console'),
    output_message = document.getElementById('output_message'),
    output_video = document.getElementById('output_video'),
    option_url = document.getElementById('option_url'),
    option_server_url = document.getElementById('option_server_url'),
    option_width = document.getElementById('option_width'),
    option_height = document.getElementById('option_height'),
    button_start = document.getElementById('button_start'),
    height = option_height.value,
    width = option_width.value,
    url = option_url.value = 'rtmp://' + location.host.split(':')[0] + ':1935/encode/124152351',
    server_url = option_server_url.value = 'http://' + location.host.split(':')[0] + ':8000';

option_height.onchange = option_height.onkeyup = function () {
    height = 1 * this.value;
};
option_width.onchange = option_width.onkeyup = function () {
    width = 1 * this.value;
};
option_url.onchange = option_url.onkeyup = function () {
    url = this.value;
};
option_server_url.onchange = option_server_url.onkeyup = function () {
    server_url = this.value;
};
button_start.onclick = requestMedia;

function video_show(stream) {
    if (window.URL) {
        output_video.src = window.URL.createObjectURL(stream);
    } else {
        output_video.src = stream;
    }
    output_video.addEventListener("loadedmetadata", function (e) {
        output_message.innerHTML = "Local video source size:" + output_video.videoWidth + "x" + output_video.videoHeight;
    }, false);
}

function show_output(str) {
    output_console.value += "\n" + str;
    output_console.scrollTop = output_console.scrollHeight;
}


navigator.getUserMedia = (navigator.getUserMedia ||
    navigator.mozGetUserMedia ||
    navigator.msGetUserMedia ||
    navigator.webkitGetUserMedia);
if (!navigator.getUserMedia) {
    fail('No getUserMedia() available.');
}
if (!MediaRecorder) {
    fail('No MediaRecorder available.');
}
var mediaRecorder;
var socket = io(server_url);

socket.on('message', function (m) {
    console.log('recv server message', m);
    show_output('SERVER:' + m);
});
socket.on('fatal', function (m) {
    show_output('ERROR: unexpected:' + m);
    alert('Error:' + m);
    mediaRecorder.stop();
});

socket.on('ffmpeg_stderr', function (m) {
    show_output('FFMPEG:' + m);
});
socket.on('disconnect', function () {
    show_output('ERROR: server disconnected!');
    mediaRecorder.stop();
});

function onSuccess(stream) {
    video_show(stream);

    socket.emit('start', url);
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start(2000);

    mediaRecorder.onstop = function (e) {
        socket.emit("disconnect");
        stream.stop();
    };

    mediaRecorder.ondataavailable = function (e) {
        socket.emit("binarystream", e.data);
    }
}

function onError(err) {
    console.log('The following error occured: ' + err);
    show_output('Local getUserMedia ERROR:' + err);
}

function requestMedia() {
    var constraints = {
        audio: true,
        video: {
            width: {min: width, ideal: width, max: width},
            height: {min: height, ideal: height, max: height}
        }
    };
    navigator.getUserMedia(constraints, onSuccess, onError);
}
function send() {
    const text = document.getElementById("input").value;

    fetch("/recommend", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text})
    })
    .then(res => res.json())
    .then(data => {

        let html = `<h3>当前情绪：${data.mood}</h3>`;

        data.songs.forEach(s => {
            html += `
            <div class="song">
                🎵 ${s.title} - ${s.artist}<br>
                <div class="reason">✨ ${s.reason}</div>
            </div>`;
        });

        document.getElementById("result").innerHTML = html;
    });
}

// 粒子加载
particlesJS.load('particles-js','/static/particles.json');
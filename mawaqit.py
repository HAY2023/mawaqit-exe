import webview
import sys
import os

# Modern HTML/CSS/JS for the MAWAQIT TV Windows Wrapper
# This uses the /tv/ player of mawaqit.net which matches the APK look
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MAWAQIT TV for Windows</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --glass-bg: rgba(255, 255, 255, 0.05);
            --accent-color: #10b981; /* Emerald for a premium feel */
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background: #000;
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }

        .splash {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: #0f172a;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            transition: opacity 1s;
        }

        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 2.5rem;
            padding: 4rem;
            width: 90%;
            max-width: 900px;
            box-shadow: 0 50px 100px -20px rgba(0, 0, 0, 0.7);
            text-align: center;
            animation: slideUp 0.8s ease-out;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(40px); }
            to { opacity: 1; transform: translateY(0); }
        }

        h1 {
            font-size: 4rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #10b981, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -2px;
        }

        .input-group {
            display: flex;
            gap: 15px;
            margin-top: 3rem;
        }

        input {
            flex: 1;
            background: rgba(0, 0, 0, 0.3);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 1.5rem;
            padding: 1.2rem 2rem;
            color: #fff;
            font-size: 1.25rem;
            outline: none;
            transition: all 0.3s;
        }

        input:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        }

        button {
            background: var(--accent-color);
            color: #fff;
            border: none;
            border-radius: 1.5rem;
            padding: 1.2rem 3rem;
            font-size: 1.25rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        button:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
        }

        .iframe-wrapper {
            position: fixed;
            top: 0; left: 0; 
            width: 100vw; height: 100vh;
            background: #000;
            display: none;
        }

        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }

        .controls {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 2000;
            display: none;
            gap: 10px;
        }

        .btn-small {
            background: rgba(0,0,0,0.6);
            border: 1px solid rgba(255,255,255,0.2);
            color: #ccc;
            padding: 8px 15px;
            border-radius: 12px;
            cursor: pointer;
            backdrop-filter: blur(5px);
            font-size: 0.8rem;
        }
        
        .loading-dots:after {
            content: '.';
            animation: dots 1.5s steps(5, end) infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60% { content: '...'; }
            80%, 100% { content: ''; }
        }
    </style>
</head>
<body>
    <div class="splash" id="ui">
        <div class="glass-card">
            <h1>MAWAQIT TV</h1>
            <p style="color: var(--text-secondary); font-size: 1.2rem;">Premium Windows Experience for Mosques</p>
            
            <div class="input-group">
                <input type="text" id="mosque-url" placeholder="Enter Mosque Name or URL..." value="paris">
                <button onclick="launch()">Start TV App</button>
            </div>
            
            <p id="msg" style="margin-top: 2rem; color: var(--text-secondary); font-style: italic;"></p>
        </div>
    </div>

    <div class="iframe-wrapper" id="player">
        <iframe id="main-frame" src=""></iframe>
    </div>

    <div class="controls" id="cntrl">
        <button class="btn-small" onclick="location.reload()">Reset App</button>
        <button class="btn-small" onclick="window.pywebview.api.toggle_fullscreen()">Full Screen</button>
    </div>

    <script>
        function launch() {
            let val = document.getElementById('mosque-url').value.trim();
            if (!val) return;

            let mosqueId = val;
            if (val.includes('mawaqit.net/')) {
                // Extract last part
                mosqueId = val.split('/').filter(p => p).pop();
            }

            const tvUrl = `https://mawaqit.net/tv/${mosqueId}`;
            
            document.getElementById('msg').innerHTML = `<span class="loading-dots">Initializing TV Player</span>`;
            
            const frame = document.getElementById('main-frame');
            frame.src = tvUrl;

            setTimeout(() => {
                document.getElementById('ui').style.opacity = '0';
                setTimeout(() => {
                    document.getElementById('ui').style.display = 'none';
                    document.getElementById('player').style.display = 'block';
                    document.getElementById('cntrl').style.display = 'flex';
                }, 1000);
            }, 1500);
        }
    </script>
</body>
</html>
"""

class API:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()

def main():
    api = API()
    window = webview.create_window(
        'MAWAQIT TV - v1.2.10',
        html=HTML_CONTENT,
        width=1280,
        height=720,
        background_color='#000000',
        js_api=api,
        min_size=(1024, 576)
    )
    api.set_window(window)
    webview.start()

if __name__ == '__main__':
    main()
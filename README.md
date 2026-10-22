#  Roblox Flowey Companion

A desktop companion inspired by Flowey from *Undertale*, designed to run alongside Roblox. The application displays Flowey on your screen and provides an interactive chat interface powered by Google's Gemini AI.

## ✨ Features

* **Flowey Companion:** Displays Flowey in a small desktop window.
* **AI Chat:** Interact with Flowey using Google's Gemini API.
* **Emotion Sprites:** Supports different Flowey expressions.
* **Voice Effects:** Supports voice sound effects when the required audio files are available.
* **Roblox Integration:** Designed to work alongside Roblox.
* **Movable Window:** Move the companion around your desktop.
* **Show and Hide:** Hide or show the companion using keyboard shortcuts.

## 🛠️ Requirements

* Windows
* Python 3.10 or newer
* Roblox (optional, depending on how you use the application)
* A Google Gemini API key
* The required image and audio assets

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Mr-Suslik/roblox-flowey-companion.git
cd roblox-flowey-companion
```

### 2. Install dependencies

```bash
pip install psutil google-genai mss pillow keyboard
```

### 3. Configure the API key

Create an environment variable named `GEMINI_API_KEY` containing your Google Gemini API key.

You can also configure `GEMINI_API_KEY_2` if your version of the application supports a second key.

**Important:** Never publish API keys, passwords, or other secrets in your repository. Do not commit files containing private credentials.

### 4. Add the required assets

Place the required Flowey sprite images in the project directory or in a `faces` subdirectory.

The application expects sprite filenames in a format similar to:

```text
Flowey 1 nice.png
Flowey 2 nice.png
```

The exact expression names may vary depending on the sprites available.

Place the default voice file next to `flowey.py`:

```text
flowey-normal-voice.wav
```

Additional emotion voice files can be added if supported by your configuration.

### 5. Run the application

Run the Python script:

```bash
python flowey.py
```

## 🎮 Controls

The default controls configured in the application are:

| Key / Action             | Function                            |
| ------------------------ | ----------------------------------- |
| `F + Y`                  | Open or activate the chat interface |
| `Z`                      | Hide the companion                  |
| `X`                      | Show the companion                  |
| `Enter`                  | Send a chat message                 |
| Left mouse button + drag | Move the window                     |
| Right-click              | Close the companion                 |

Controls may vary if the source code has been modified.

## 🔑 API Key Security

This application uses the Google Gemini API.

* Keep API keys private.
* Store credentials in environment variables rather than directly in source code.
* Never upload API keys to GitHub.
* If a key has been exposed publicly, revoke it and generate a replacement.

## 🎨 Third-Party Assets and Credits

This project is inspired by *Undertale* and uses a Flowey-inspired visual design.

The project author does not claim ownership of third-party sprites, fonts, sounds, or other assets.

* **Undertale:** Intellectual property of Toby Fox.
* **Determination Mono (RUS BY LYAJK):** A third-party font based on 8-bit Operator. Copyright notices associated with the font credit Grand Chaos Productions, Leafia_Barrett, and theFIZZYnator.
* **Flowey sprites:** Obtained from The Spriters Resource.

Font source: https://online-fonts.com/fonts/determination-monorus-lyajk

Sprite resource: https://www.spriters-resource.com/

Third-party assets are subject to their respective copyright terms and licenses. This repository does not grant permission to redistribute assets owned by other parties. Unless redistribution permission has been confirmed, third-party asset files should not be included in this repository.

## ⚠️ Disclaimer

This is an unofficial fan-made project. It is not affiliated with, endorsed by, or sponsored by Toby Fox, the creators of *Undertale*, Roblox, or Google.

All trademarks and third-party materials belong to their respective owners.

## 📄 License

The license for the original code in this repository does not automatically apply to third-party assets.

If a license file is added, it applies only to the materials that the project author has the right to license. Third-party materials remain subject to their respective terms.

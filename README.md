# WebGUI

A simple Python GUI framework that uses HTML as the interface.

WebGUI lets you make Python applications with a web browser as the GUI without needing to write JavaScript.

## Installation

```bash
pip install webgui-py
```

## Basic Example


```python
import webgui
import time

webgui.init()

webgui.send("index.html")

while webgui.running():

	if webgui.button("say hello").clicked:
		print("Hello!")

	time.sleep(0.05)
```


```html
<!DOCTYPE html>
<html>

<body>

<h1>My App</h1>

<p>Hello!</p>

<button name="say hello">Say Hello</button>

</body>

</html>
```

## Getting Input

You can also ask the user for text:

```python
name = webgui.get_input("What's your name?")

print(name)
```

The browser displays an input box and returns what the user entered.

## Audio

WebGUI includes audio features for playing, looping, and stopping audio files.

You can play an audio file with:

```python
webgui.audio.play("music.mp3", False)
```

The play() function takes two arguments:
filename — the path to the audio file.
loop — True to loop the audio or False to play it once.
You can stop the audio with:
```python
webgui.audio.stop()
```

## Why WebGUI?

WebGUI is designed to be simple.

You write your interface using HTML and control your application using Python.

You don't need to write JavaScript or deal directly with HTTP communication.

## Features

* HTML-based GUI
* Python controls the application
* Automatic browser opening
* Simple button handling
* Text input
* audio player
* Multiple HTML pages
* No JavaScript required in your application

## License

See the LICENSE file.

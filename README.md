# WebGUI

A simple Python GUI framework that uses HTML as the interface.

WebGUI lets you make Python applications with a web browser as the GUI without needing to write JavaScript.

## Installation

```bash
pip install webgui
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
* Multiple HTML pages
* No JavaScript required in your application

## License

See the LICENSE file.

# WebGUI

WebGUI lets a Python program use a web browser as its graphical interface. You can create the page with ordinary HTML or with WebGUI's small `.ui` text format, then handle button clicks and text input from Python.

## Installation

```bash
pip install webgui-py
```

## Quick start with a `.ui` page

Create `settings.ui` next to your Python program:

```text
tle: "Settings"
h1: "Game Settings"
txt: "Music"
btn: "music on"
btn: "music off"
btn: "close"
```

Then use it from Python:

```python
import time
import webgui

webgui.init()
webgui.send("settings.ui")

music_on = webgui.button("music on")
music_off = webgui.button("music off")
close = webgui.button("close")

while webgui.running():
	if music_on.clicked:
		print("Music enabled")
	if music_off.clicked:
		print("Music disabled")
	if close.clicked:
		webgui.close()
	time.sleep(0.05)
```

`init()` starts the local web server and opens the browser. `send()` displays the selected page. The loop checks button events and should sleep briefly between checks so it does not use a CPU core continuously.

## The `.ui` language

Each nonblank line contains one instruction in the form `instruction: "value"`. Values are quoted strings, so spaces and punctuation stay part of the value. Instructions are case-sensitive and are processed in file order. The supported instructions are:

| Instruction | Result |
| --- | --- |
| `textincoding: "utf-8"` | Selects the file encoding. UTF-8 is the default. Put this declaration on its own line; common encodings such as `utf-8` and `latin-1` are supported. |
| `tle: "Settings"` | Sets the page title. |
| `title: "Settings"` | Alias for `tle`. |
| `h1: "Heading"` | Adds an H1 heading. |
| `txt: "Paragraph"` | Adds a paragraph. |
| `btn: "Save changes"` | Adds a button whose visible text and Python button name are both exactly `Save changes`. |

You may use single or double quotes. An empty string is valid, for example `txt: ""`. Escape a quote inside a value with a backslash, such as `txt: "She said \\\"hello\\\""`. Blank lines and lines starting with `#` or `//` are ignored:

```text
textincoding: "utf-8"
# This is a comment
tle: "My page"

h1: "Welcome"
txt: "Text with spaces, punctuation, and Unicode: café ☕"
btn: "Save & continue!"
```

Text is HTML-escaped when the page is generated, so characters such as `<`, `>`, and `&` display as text rather than being treated as markup. A button's full quoted string is its name: `btn: "Save & continue!"` is handled in Python with `webgui.button("Save & continue!")`. Spaces, punctuation, and Unicode are supported.

The title is placed in the document's `<head>`; headings, paragraphs, and buttons appear in the order they occur in the file. You can include multiple headings, text lines, and buttons.

Invalid instructions, unsupported names, invalid encodings, and decoding errors are shown in the page with the source filename and line number when available. A bad `.ui` file displays an error page instead of stopping the server; correcting the file lets it load normally.

## Using ordinary HTML

HTML files continue to work with `send()`:

```python
import time
import webgui

webgui.init()
webgui.send("index.html")

hello = webgui.button("say hello")
while webgui.running():
	if hello.clicked:
		print("Hello!")
	time.sleep(0.05)
```

Add a `name` attribute to any HTML button you want Python to detect. The button's displayed text can differ from its name:

```html
<!DOCTYPE html>
<html>
<head><title>My App</title></head>
<body>
	<h1>My App</h1>
	<p>Hello!</p>
	<button type="button" name="say hello">Say Hello</button>
</body>
</html>
```

`webgui.button(name)` returns a button object. Its `.clicked` property is true once when a matching click has arrived, then false until the next click. Button names are matched exactly, including spaces and capitalization.

## Text input

`get_input()` displays a text prompt in the browser and returns the submitted value:

```python
name = webgui.get_input("What's your name?")
print("Hello, " + name)
```

Call it after `webgui.init()`. The input prompt temporarily appears over the current page.

## Pages, refresh, and cache

`send()` accepts `.html` and `.ui` paths. You can call it again to show another page. The browser checks for page changes and refreshes automatically. `.ui` HTML is generated in memory, cached separately for each file, and regenerated when the source file changes.

If your program needs to force regeneration, call:

```python
webgui.clear_html_cache()
```

This clears the generated page cache and asks the displayed browser page to refresh. No generated HTML files are written to disk.

## Other functions

- `webgui.init(port=5000, open_browser=True)` starts the local server. Pass `open_browser=False` to open the page yourself.
- `webgui.send(filename)` displays an HTML or `.ui` file.
- `webgui.button(name)` returns an object whose `.clicked` property reports a click.
- `webgui.get_input(question)` displays a prompt and returns the submitted text.
- `webgui.running()` reports whether the application is running.
- `webgui.close()` marks the application as stopped.
- `webgui.audio.play(filename, loop=False)` plays an audio file; `webgui.audio.stop()` stops playback.

## License

See [LICENSE](LICENSE).

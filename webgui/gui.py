from flask import Flask, request, Response, redirect
import threading
import time
import webbrowser
import os
import re
import urllib.parse


app = Flask(__name__)


_current_page = ""
_buttons_clicked = []

_running = False
_server_thread = None
_port = 5000

_input_value = None
_input_waiting = False
_input_question = ""


# ============================================================
# INTERNAL HTML PROCESSING
# ============================================================

def _process_html(html):

	pattern = r'<button([^>]*)name=["\']([^"\']+)["\']([^>]*)>'

	def replace_button(match):

		before = match.group(1)
		name = match.group(2)
		after = match.group(3)

		encoded_name = urllib.parse.quote(name)

		return (
			f'<button{before}name="{name}"{after} '
			f'onclick="fetch(\'/__gui_button?name={encoded_name}\')'
			f'.then(() => window.location.reload()); '
			f'return false;">'
		)

	return re.sub(
		pattern,
		replace_button,
		html
	)


def _read_page():

	if not _current_page:
		return """
		<!DOCTYPE html>
		<html>
		<head>
			<title>WebGUI</title>
		</head>
		<body>
			<h1>No page has been sent.</h1>
		</body>
		</html>
		"""

	if not os.path.isfile(_current_page):

		return f"""
		<!DOCTYPE html>
		<html>
		<head>
			<title>WebGUI Error</title>
		</head>
		<body>
			<h1>File not found</h1>
			<p>{_current_page}</p>
		</body>
		</html>
		"""

	try:

		with open(
			_current_page,
			"r",
			encoding="utf-8"
		) as file:

			html = file.read()

	except Exception as error:

		return f"""
		<!DOCTYPE html>
		<html>
		<head>
			<title>WebGUI Error</title>
		</head>
		<body>
			<h1>Could not read page</h1>
			<p>{error}</p>
		</body>
		</html>
		"""

	return _process_html(html)


# ============================================================
# WEB SERVER
# ============================================================

@app.route("/")
def _page():

	if _input_waiting:

		question = _input_question

		return f"""
		<!DOCTYPE html>
		<html>

		<head>
			<title>Input</title>
		</head>

		<body>

			<h1>Input</h1>

			<p>{question}</p>

			<form method="post" action="/__gui_input">

				<input
					type="text"
					name="value"
					autofocus
				>

				<button type="submit">
					Submit
				</button>

			</form>

		</body>

		</html>
		"""

	return Response(
		_read_page(),
		content_type="text/html; charset=utf-8"
	)


@app.route("/__gui_button", methods=["GET", "POST"])
def _button_clicked():

	name = request.args.get("name")

	if name:
		_buttons_clicked.append(name)

	return "", 204


@app.route("/__gui_input", methods=["POST"])
def _input_submitted():

	global _input_value
	global _input_waiting

	_input_value = request.form.get(
		"value",
		""
	)

	_input_waiting = False

	return redirect("/")


# ============================================================
# GUI FUNCTIONS
# ============================================================

def init(port=5000, open_browser=True):

	global _running
	global _server_thread
	global _port

	if _running:
		return

	_port = port
	_running = True

	def run_server():

		app.run(
			host="127.0.0.1",
			port=_port,
			debug=False,
			use_reloader=False,
			threaded=True
		)

	_server_thread = threading.Thread(
		target=run_server,
		daemon=True
	)

	_server_thread.start()

	time.sleep(1)

	if open_browser:

		webbrowser.open(
			f"http://127.0.0.1:{_port}"
		)


def send(filename):

	global _current_page

	_current_page = os.path.abspath(filename)


def button(name):

	return Button(name)


def running():

	return _running


def close():

	global _running

	_running = False


def get_input(question):

	global _input_value
	global _input_waiting
	global _input_question

	_input_value = None
	_input_question = question
	_input_waiting = True

	while _input_value is None:

		if not _running:
			return ""

		time.sleep(0.05)

	value = _input_value

	_input_value = None

	return value


# ============================================================
# BUTTON
# ============================================================

class Button:

	def __init__(self, name):

		self.name = name

	@property
	def clicked(self):

		if self.name in _buttons_clicked:

			_buttons_clicked.remove(self.name)

			return True

		return False
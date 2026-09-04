from flask import Flask, request, Response
import threading
import time
import webbrowser
import os
import re
import urllib.parse
import html


app = Flask(__name__)


_current_page = ""
_page_version = 0

_running = False

_server_thread = None
_port = 5000


# ============================================================
# BUTTON SYSTEM
# ============================================================

_button_events = []
_button_lock = threading.Lock()


# ============================================================
# INPUT SYSTEM
# ============================================================

_input_value = None
_input_waiting = False
_input_question = ""

_input_lock = threading.Lock()


# ============================================================
# HTML PROCESSING
# ============================================================

def _process_html(source):

	pattern = r'<button([^>]*)name=["\']([^"\']+)["\']([^>]*)>'

	def replace_button(match):

		before = match.group(1)
		name = match.group(2)
		after = match.group(3)

		encoded_name = urllib.parse.quote(
			name,
			safe=""
		)

		return (
			f'<button{before}'
			f'name="{html.escape(name)}"'
			f'{after} '
			f'onclick="webguiButton(\'{encoded_name}\'); '
			f'return false;">'
		)

	return re.sub(
		pattern,
		replace_button,
		source
	)


# ============================================================
# READ HTML PAGE
# ============================================================

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

<p>{html.escape(_current_page)}</p>

</body>

</html>
"""


	try:

		with open(
			_current_page,
			"r",
			encoding="utf-8"
		) as file:

			source = file.read()

	except Exception as error:

		return f"""
<!DOCTYPE html>
<html>

<head>
	<title>WebGUI Error</title>
</head>

<body>

<h1>Could not read page</h1>

<p>{html.escape(str(error))}</p>

</body>

</html>
"""

	return _process_html(source)


# ============================================================
# NO-CACHE RESPONSE
# ============================================================

def _no_cache_response(content, content_type):

	response = Response(
		content,
		content_type=content_type
	)

	response.headers["Cache-Control"] = (
		"no-store, no-cache, must-revalidate, max-age=0"
	)

	response.headers["Pragma"] = "no-cache"

	response.headers["Expires"] = "0"

	return response


# ============================================================
# BROWSER PAGE
# ============================================================

@app.route("/")
def _page():

	page = _read_page()

	script = f"""
<script>

const webguiPageVersion = { _page_version };


function webguiButton(name) {{

	fetch(
		"/__gui_button?name=" + name,
		{{
			cache: "no-store"
		}}
	);

}}


function webguiCheckPage() {{

	fetch(
		"/__gui_page_version?time=" + Date.now(),
		{{
			cache: "no-store"
		}}
	)

	.then(function(response) {{

		return response.text();

	}})

	.then(function(version) {{

		if (version !== String(webguiPageVersion)) {{

			window.location.assign(
				"/?webgui_version=" + version
			);

		}}

	}})

	.catch(function(error) {{

		console.log(
			"WebGUI page check error:",
			error
		);

	}})

	.finally(function() {{

		setTimeout(
			webguiCheckPage,
			100
		);

	}});

}}


webguiCheckPage();

</script>
"""

	if "</head>" in page:

		page = page.replace(
			"</head>",
			script + "</head>",
			1
		)

	else:

		page = script + page

	return _no_cache_response(
		page,
		"text/html; charset=utf-8"
	)


# ============================================================
# BUTTON
# ============================================================

@app.route("/__gui_button", methods=["GET"])
def _button_clicked():

	name = request.args.get(
		"name",
		""
	)

	if not name:

		return "", 204

	with _button_lock:

		_button_events.append(name)

	return "", 204


# ============================================================
# PAGE VERSION
# ============================================================

@app.route("/__gui_page_version", methods=["GET"])
def _page_version_request():

	return _no_cache_response(
		str(_page_version),
		"text/plain; charset=utf-8"
	)


# ============================================================
# CURRENT PAGE
# ============================================================

@app.route("/__gui_page", methods=["GET"])
def _current_page_request():

	return _no_cache_response(
		_read_page(),
		"text/html; charset=utf-8"
	)


# ============================================================
# INPUT
# ============================================================

@app.route("/__gui_input", methods=["POST"])
def _input_submitted():

	global _input_value
	global _input_waiting

	value = request.form.get(
		"value",
		""
	)

	with _input_lock:

		_input_value = value
		_input_waiting = False

	return _no_cache_response(
		_read_page(),
		"text/html; charset=utf-8"
	)


# ============================================================
# INIT
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


# ============================================================
# SEND
# ============================================================

def send(filename):

	global _current_page
	global _page_version

	_current_page = os.path.abspath(
		filename
	)

	_page_version += 1


# ============================================================
# BUTTON OBJECT
# ============================================================

def button(name):

	return Button(name)


class Button:

	def __init__(self, name):

		self.name = name

	@property
	def clicked(self):

		with _button_lock:

			if self.name in _button_events:

				_button_events.remove(
					self.name
				)

				return True

		return False


# ============================================================
# RUNNING
# ============================================================

def running():

	return _running


# ============================================================
# CLOSE
# ============================================================

def close():

	global _running

	_running = False


# ============================================================
# INPUT
# ============================================================

def get_input(question):

	global _input_value
	global _input_waiting
	global _input_question

	with _input_lock:

		_input_value = None
		_input_question = question
		_input_waiting = True

	while True:

		with _input_lock:

			if _input_value is not None:

				value = _input_value

				_input_value = None

				return value

		if not _running:

			return ""

		time.sleep(0.05)
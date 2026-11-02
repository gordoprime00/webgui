from flask import Flask, request, Response
from werkzeug.serving import make_server
import threading
import time
import webbrowser
import os
import re
import urllib.parse
import html
import ast
import subprocess
import sys


app = Flask(__name__)


_current_page = ""
_page_version = 0

_html_cache = {}
_html_cache_lock = threading.Lock()
_page_file_signature = None

_running = False

_server_thread = None
_server = None
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
		name = html.unescape(match.group(2))
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


_UI_INSTRUCTIONS = {
	"tle": lambda value: f"<title>{html.escape(value)}</title>",
	"title": lambda value: f"<title>{html.escape(value)}</title>",
	"h1": lambda value: f"<h1>{html.escape(value)}</h1>",
	"txt": lambda value: f"<p>{html.escape(value)}</p>",
	"btn": lambda value: (
		f'<button type="button" name="{html.escape(value, quote=True)}">'
		f'{html.escape(value)}</button>'
	),
}


def _ui_error(filename, message, line=None):
	location = f"{filename}:{line}" if line is not None else str(filename)
	return ValueError(f"{location}: {message}")


def _parse_ui(filename, source):
	lines = source.splitlines()
	body = []
	title = None
	for line_number, line in enumerate(lines, 1):
		stripped = line.strip()
		if not stripped or stripped.startswith("#") or stripped.startswith("//"):
			continue
		match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.+?)\s*", stripped)
		if not match:
			raise _ui_error(filename, "expected instruction: quoted value", line_number)
		name, literal = match.groups()
		try:
			value = ast.literal_eval(literal)
		except (SyntaxError, ValueError) as error:
			raise _ui_error(filename, "expected a quoted string", line_number) from error
		if not isinstance(value, str):
			raise _ui_error(filename, "instruction value must be a string", line_number)
		if name == "textincoding":
			continue
		generator = _UI_INSTRUCTIONS.get(name)
		if generator is None:
			raise _ui_error(filename, f"unsupported instruction {name!r}", line_number)
		if name in ("tle", "title"):
			title = generator(value)
		else:
			body.append(generator(value))
	return "<!DOCTYPE html>\n<html>\n<head>" + (title or "<title>WebGUI</title>") + "</head>\n<body>\n" + "\n".join(body) + "\n</body>\n</html>"


def _load_ui(filename, stat_result):
	signature = (stat_result.st_mtime_ns, stat_result.st_size)
	with _html_cache_lock:
		cached = _html_cache.get(filename)
		if cached and cached[0] == signature:
			return cached[1]
	try:
		with open(filename, "rb") as file:
			data = file.read()
		# Encoding declaration is ASCII-compatible and can be read before decoding.
		declaration = re.search(rb"(?im)^\s*textincoding\s*:\s*(['\"])([^'\"]+)\1\s*(?:#.*)?$", data)
		encoding = declaration.group(2).decode("ascii") if declaration else "utf-8-sig"
		try:
			"".encode(encoding)
		except LookupError as error:
			line = data[:declaration.start()].count(b"\n") + 1 if declaration else 1
			raise _ui_error(filename, f"invalid encoding name {encoding!r}", line) from error
		try:
			source = data.decode(encoding)
		except UnicodeDecodeError as error:
			line = data[:error.start].count(b"\n") + 1
			raise _ui_error(filename, f"file cannot be decoded as {encoding}", line) from error
		page = _parse_ui(filename, source)
	except OSError as error:
		raise _ui_error(filename, f"could not read file: {error}") from error
	with _html_cache_lock:
		_html_cache[filename] = (signature, page)
	return page


def clear_html_cache():
	global _page_version
	with _html_cache_lock:
		_html_cache.clear()
	_page_version += 1


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
		if os.path.splitext(_current_page)[1].lower() == ".ui":
			page = _load_ui(_current_page, os.stat(_current_page))
		else:
			with open(_current_page, "r", encoding="utf-8") as file:
				page = file.read()

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

	return _process_html(page)


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

	with _input_lock:
		input_waiting = _input_waiting
		input_question = _input_question

	if input_waiting:
		input_ui = f'''
<form action="/__gui_input" method="post" style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#0008;z-index:2147483647">
	<div style="background:white;color:black;padding:1.5em;border-radius:.5em;max-width:90%;box-shadow:0 2px 12px #0008">
		<label>{html.escape(str(input_question))}<br>
			<input type="text" name="value" autofocus style="margin-top:.75em">
		</label>
		<button type="submit" style="margin-left:.5em">Submit</button>
	</div>
</form>
'''
		if "</body>" in page:
			page = page.replace("</body>", input_ui + "</body>", 1)
		else:
			page += input_ui

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
	global _page_version
	global _page_file_signature
	if _current_page and os.path.splitext(_current_page)[1].lower() == ".ui":
		try:
			stat_result = os.stat(_current_page)
			signature = (stat_result.st_mtime_ns, stat_result.st_size)
		except OSError:
			signature = None
		if _page_file_signature is not None and signature != _page_file_signature:
			_page_version += 1
		_page_file_signature = signature

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
	global _page_version

	value = request.form.get(
		"value",
		""
	)

	with _input_lock:

		_input_value = value
		_input_waiting = False
		_page_version += 1

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
	global _server
	global _port

	if _running:
		return

	_port = port

	try:
		_server = make_server(
			"127.0.0.1",
			_port,
			app,
			threaded=True
		)
	except Exception:
		_server = None
		_running = False
		raise

	_running = True

	def run_server():
		try:
			_server.serve_forever()
		finally:
			pass

	_server_thread = threading.Thread(
		target=run_server,
		daemon=True
	)

	_server_thread.start()

	time.sleep(0.2)

	if open_browser and _running:
		webbrowser.open(
			f"http://127.0.0.1:{_port}"
		)

# ============================================================
# SEND
# ============================================================

def send(filename):

	global _current_page
	global _page_version
	global _page_file_signature

	_current_page = os.path.abspath(
		filename
	)

	_page_version += 1
	try:
		stat_result = os.stat(_current_page)
		_page_file_signature = (stat_result.st_mtime_ns, stat_result.st_size)
	except OSError:
		_page_file_signature = None


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

def _close_browser_tab():

	if sys.platform != "darwin":
		return

	url_prefix = f"http://127.0.0.1:{_port}"

	script = f"""
	set targetPrefix to "{url_prefix}"

	try
		tell application "Safari"
			if it is running then
				repeat with browserWindow in windows
					repeat with browserTab in tabs of browserWindow
						if (URL of browserTab) starts with targetPrefix then
							close browserTab
						end if
					end repeat
				end repeat
			end if
		end tell
	end try

	try
		tell application "Google Chrome"
			if it is running then
				repeat with browserWindow in windows
					set tabIndex to (count of tabs of browserWindow)
					repeat while tabIndex > 0
						if (URL of tab tabIndex of browserWindow) starts with targetPrefix then
							close tab tabIndex of browserWindow
						end if
						set tabIndex to tabIndex - 1
					end repeat
				end repeat
			end if
		end tell
	end try

	try
		tell application "Brave Browser"
			if it is running then
				repeat with browserWindow in windows
					set tabIndex to (count of tabs of browserWindow)
					repeat while tabIndex > 0
						if (URL of tab tabIndex of browserWindow) starts with targetPrefix then
							close tab tabIndex of browserWindow
						end if
						set tabIndex to tabIndex - 1
					end repeat
				end repeat
			end if
		end tell
	end try

	try
		tell application "Microsoft Edge"
			if it is running then
				repeat with browserWindow in windows
					set tabIndex to (count of tabs of browserWindow)
					repeat while tabIndex > 0
						if (URL of tab tabIndex of browserWindow) starts with targetPrefix then
							close tab tabIndex of browserWindow
						end if
						set tabIndex to tabIndex - 1
					end repeat
				end repeat
			end if
		end tell
	end try
	"""

	try:
		subprocess.run(
			["osascript", "-e", script],
			capture_output=True,
			text=True,
			timeout=5,
			check=False
		)
	except (OSError, subprocess.TimeoutExpired):
		pass


def close():

	global _running
	global _server
	global _server_thread
	global _input_value
	global _input_waiting
	global _input_question
	global _page_version

	if not _running and _server is None:
		return

	_running = False
	_page_version += 1

	with _input_lock:
		_input_value = None
		_input_waiting = False
		_input_question = ""

	with _button_lock:
		_button_events.clear()

	_close_browser_tab()

	server = _server
	thread = _server_thread

	_server = None
	_server_thread = None

	if server is not None:
		server.shutdown()
		server.server_close()

	if thread is not None and thread.is_alive():
		thread.join(timeout=3)

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

	global _page_version
	_page_version += 1

	while True:

		with _input_lock:

			if _input_value is not None:

				value = _input_value

				_input_value = None

				return value

		if not _running:

			return ""

		time.sleep(0.05)

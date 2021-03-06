"""Web routes for focusgrouplogs."""


import os
import sys
import traceback
from flask import abort
from flask import Response
from flask import render_template

from focusgrouplogs import app
from focusgrouplogs import cache
from focusgrouplogs import FOCUS_GROUPS
from focusgrouplogs import BACKEND

from focusgrouplogs.backends import backends
from focusgrouplogs.backends import migration

db = backends[BACKEND]
TRANSITION_HAS_RUN = False


@cache.cached(timeout=None)
def get_style():
    """Reads and returns the inline css styling."""

    style = os.path.join(os.path.dirname(__file__), "templates", "style.css")
    with open(style, "r") as opencss:
        return opencss.read().strip()


@app.route("/<regex('({})'):group>/<date>/".format("|".join(FOCUS_GROUPS)),
           methods=["GET"])
@app.route("/<regex('({})'):group>/".format("|".join(FOCUS_GROUPS)),
           methods=["GET"])
@cache.memoize(timeout=60)
def group_get(group, date=None):
    """Displays the most recent day for a group (or specific)."""

    if date is None:
        group_logs = db.all_content(group)
    else:
        group_logs = [db.log_content(group, date)]

    return render_template(
        "logs.html",
        focus_group=group,
        log_days=group_logs,
        css=get_style(),
    )


@app.route("/")
@cache.cached(timeout=3600)
def main_index():
    """Displays links to the focus groups, fairly static."""

    return render_template(
        "index.html",
        groups=[{"name": f, "logs": db.log_metadata(f)} for f in FOCUS_GROUPS],
        css=get_style(),
    )


@app.route("/migrate")
def migrate_template():
    global TRANSITION_HAS_RUN
    if os.environ.get("TRANSITION_TO_DATASTORE") and not TRANSITION_HAS_RUN:
        return render_template("stream.html")
    else:
        abort(404)


@app.route("/do_migrate")
def migrate_from_files():
    global TRANSITION_HAS_RUN
    if os.environ.get("TRANSITION_TO_DATASTORE") and not TRANSITION_HAS_RUN:
        TRANSITION_HAS_RUN = True
        return Response(
            migration.transition_to_datastore(),
            mimetype="text/event-stream",
        )
    else:
        abort(404)


def traceback_formatter(excpt, value, tback):
    """Catches all exceptions and re-formats the traceback raised."""

    sys.stdout.write("".join(traceback.format_exception(excpt, value, tback)))


def hook_exceptions():
    """Hooks into the sys module to set our formatter."""

    if hasattr(sys.stdout, "fileno"):  # when testing, sys.stdout is StringIO
        # reopen stdout in non buffered mode
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        # set the hook
        sys.excepthook = traceback_formatter


def paste(*_, **settings):
    """For paste, start and return the Flask app."""

    hook_exceptions()
    return app


def main():
    """Debug/cmdline entry point."""

    paste().run(
        host="0.0.0.0",
        port=8080,
        debug=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()

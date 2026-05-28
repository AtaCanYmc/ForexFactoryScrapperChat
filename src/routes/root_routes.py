import logging
from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

root_bp = Blueprint("root", __name__)


@root_bp.route("/", methods=["GET"])
def welcome():
    """Render the chat UI page."""
    try:
        return render_template("chat.html"), 200
    except Exception as e:
        logger.exception(f"Failed to render chat template: {e}")
        return "<html><body><h1>Chat</h1></body></html>", 200

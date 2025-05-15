import logging

from mkdocs.__main__ import ColorFormatter
from termcolor import colored

def get_custom_logger(name: str) -> logging.Logger:
    """
    Return a custom logger.

    Arguments:
        name: The name to use with `logging.getLogger`.

    Returns:
        A logging.Logger instance.
    """
    plugin_name = name.split(".")[0]
    logger = logging.getLogger(f"mkdocs.plugins.{plugin_name}")
    logger.propagate = False
    if not logger.handlers: # pragma no branch
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(CustomColorFormatter(plugin_name))
        logger.addHandler(handler)
    return logger


class CustomColorFormatter(ColorFormatter):
    """
    Custom formatter, extending the mkdocs.__main__.ColorFormatter to add a custom colored
    plugin name prefix to the log messages.
    """

    plugin_prefix_color = "light_blue"

    def __init__(self, prefix: str):
        super().__init__()
        self.prefix = prefix

    def format(self, record):
        message = logging.Formatter().format(record)
        # Set prefixes
        level_prefix = f"{record.levelname:<8}-  "
        level_prefix_length = len(level_prefix)
        uncolored_plugin_prefix = f"[{self.prefix}]"
        colored_plugin_prefix = colored(
            uncolored_plugin_prefix, self.plugin_prefix_color
        )

        # Set prefixed message with uncolored plugin prefix before wrapping
        uncolored_prefixed_message = f"{uncolored_plugin_prefix} {message}"

        if self.text_wrapper.width:
            # Wrap the uncolored message if the terminal width is detected
            wrapped_lines = self.text_wrapper.fill(
                uncolored_prefixed_message
            ).splitlines()
            # Replace the plugin prefix with the colored one and
            # remove the indentation from the first wrapped line
            if wrapped_lines: # pragma no branch
                wrapped_lines[0] = wrapped_lines[0][level_prefix_length:].replace(
                    uncolored_plugin_prefix, colored_plugin_prefix, 1
                )
            msg = "\n".join(wrapped_lines)
        else:
            msg = f"{colored_plugin_prefix} {message}"

        # Color the level prefix
        if record.levelname in self.colors:
            level_prefix = colored(level_prefix, self.colors[record.levelname])
        return f"{level_prefix}{msg}"

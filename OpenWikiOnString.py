"""
OpenWikiOnString.py - Sublime Text Plugin for Pawn/open.mp

Opens the open.mp documentation for the currently selected text.
If nothing is selected, tries to intelligently find a function or constant
under the cursor. Provides user feedback for errors and missing pages.

Original concept: Southclaws
Improved for open.mp and modern Sublime Text (ST3+).
"""

import sublime
import sublime_plugin
import webbrowser
import urllib.parse


# Base URL for the open.mp documentation.
# The original script hardcoded "https://open.mp/docs/", but the actual
# documentation site uses this format. Adjust if the URL structure changes.
OPEN_MP_DOCS_BASE = "https://open.mp/docs"


class OpenWikiOnStringCommand(sublime_plugin.TextCommand):
    """
    Opens the open.mp wiki page for the selected text or the identifier
    under the cursor when the command is run.
    """

    def run(self, edit):
        """
        Executes the command. Gets the query string and opens the browser.
        """
        query = self._get_query_string()
        if not query:
            sublime.status_message("[Pawn] No valid identifier found to search for.")
            return

        url = self._build_url(query)
        self._open_in_browser(url, query)

    # ---- Internal Helpers ----

    def _get_query_string(self):
        """
        Returns the string to search for, either from the current selection
        or by expanding to the word under the cursor.
        """
        view = self.view
        sel = view.sel()

        # Check if there is a non-empty selection first.
        if sel and not sel[0].empty():
            return view.substr(sel[0]).strip()

        # No selection: try to find the identifier at the cursor position.
        if sel:
            cursor_pos = sel[0].begin()
            # Expand the selection to the word under the cursor.
            word_region = view.word(cursor_pos)
            word = view.substr(word_region)
            # Check if it looks like a valid Pawn identifier (starts with letter/underscore).
            if word and (word[0].isalpha() or word[0] == '_'):
                return word

        return None

    def _build_url(self, query):
        """
        Constructs the full open.mp documentation URL for the given query.
        Properly encodes the query string to handle special characters.
        
        Args:
            query (str): The function/constant name to look up.
        
        Returns:
            str: The complete URL to open.
        """
        # Encode the query for URLs, preserving slashes if they are part of the name.
        # Also convert spaces, which might appear if the user selected multiple words.
        encoded_query = urllib.parse.quote(query.strip(), safe='')
        return f"{OPEN_MP_DOCS_BASE}{encoded_query}"

    def _open_in_browser(self, url, query):
        """
        Opens the URL in the default web browser and shows a status message.
        
        Args:
            url (str): The full URL to open.
            query (str): The original search term (for the status bar).
        """
        try:
            webbrowser.open_new_tab(url)
            sublime.status_message(f"[Pawn] Opened open.mp docs for '{query}'")
        except Exception as e:
            sublime.error_message(f"[Pawn] Failed to open browser: {e}")
            print(f"[OpenWikiOnString] Error opening URL '{url}': {e}")
"""Dark, keyboard-accessible presentation layer for the desktop launcher.

Visual system matches the redesigned overlays: deep navy surfaces, one violet accent,
mint reserved for the running state.
"""

import base64
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from desktop_branding import icon_png
from spotify_app_config import PUBLIC_CLIENT_ID


BACKGROUND = '#0b0d12'
SIDEBAR = '#0e1118'
SURFACE = '#141822'
SURFACE_2 = '#1a1f2b'
INPUT = SURFACE_2
BORDER = '#262c3a'
TEXT = '#f4f6fb'
MUTED = '#9aa3b5'
ACCENT = '#8b7cff'
ACCENT_DARK = '#2a2650'
ACCENT_TEXT = '#120e2e'
SUCCESS = '#6fe3b4'
SUCCESS_DARK = '#1d3a34'
AMBER = '#f3ce8e'
ERROR = '#ff9aa7'
ERROR_DARK = '#3a2230'

PAGES = {
    'home': ('Home', 'Welcome back.', 'See where your session stands and what is left to set up.'),
    'setup': ('Stream setup', 'Make it your stream.', 'Choose your chat source and where your overlays will run.'),
    'overlays': ('Overlay links', 'Your stream, connected.', 'Copy a browser-source link into OBS or TikTok Studio.'),
    'connections': ('Connections', 'Bring the music.', 'Connect your own accounts. Spotify is completely optional.'),
    'preferences': ('Preferences', 'The details, your way.', 'Tune voting, moderation, and your local workspace.'),
}
LINK_NAMES = ('Skip overlay', 'Queue overlay', 'Control panel')
LINK_HINTS = {
    'Skip overlay': 'OBS: add a Browser source at 420 × 760 with a transparent background. Any size works; the meter scales.',
    'Queue overlay': 'OBS: add a Browser source at 520 × 860 (portrait) or 1280 × 720 (landscape). It fills the size you give it.',
    'Control panel': 'Open this in your own browser only. Never add it to a scene or share the link.',
}
SESSION_STATES = {
    'stopped': ('Not running', MUTED, 'Ready to start'),
    'starting': ('Starting…', AMBER, 'Getting your widget ready'),
    'running': ('Running', SUCCESS, 'Widget server running'),
    'stopping': ('Stopping…', AMBER, 'Closing your session'),
}


def initial_window_geometry(root):
    width = min(1120, max(900, root.winfo_screenwidth() - 80))
    height = min(820, max(620, root.winfo_screenheight() - 100))
    return f'{width}x{height}'


def _installed(family, fallback='Segoe UI'):
    try:
        return family if family in set(tkfont.families()) else fallback
    except tk.TclError:
        return fallback


def display_font():
    """Heading family: Segoe UI Variable Display on Windows 11, Segoe UI elsewhere."""
    return _installed('Segoe UI Variable Display')


def text_font():
    """Body family: Segoe UI Variable Text on Windows 11, Segoe UI elsewhere."""
    return _installed('Segoe UI Variable Text')


class Switch(tk.Canvas):
    """A drawn toggle switch bound to a BooleanVar, with a ttk-like state API."""

    WIDTH, HEIGHT = 44, 24

    def __init__(self, parent, variable, background=SURFACE):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT, background=background,
                         highlightthickness=2, highlightbackground=background, highlightcolor=ACCENT,
                         borderwidth=0, cursor='hand2', takefocus=True)
        self.variable = variable
        self._disabled = False
        self._trace = variable.trace_add('write', lambda *arguments: self._draw())
        self.bind('<Button-1>', lambda event: self.toggle())
        self.bind('<space>', lambda event: self.toggle())
        self.bind('<Return>', lambda event: self.toggle())
        self.bind('<Destroy>', self._release, add='+')
        self._draw()

    def _release(self, event=None):
        try:
            self.variable.trace_remove('write', self._trace)
        except Exception:
            pass

    def toggle(self):
        if self._disabled:
            return 'break'
        self.variable.set(not self.variable.get())
        return 'break'

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        state = kwargs.pop('state', None)
        if state is not None:
            self._disabled = state == 'disabled'
            self.configure_cursor()
        result = super().configure(cnf, **kwargs) if (cnf is not None or kwargs) else None
        self._draw()
        return result

    config = configure

    def configure_cursor(self):
        super().configure(cursor='arrow' if self._disabled else 'hand2', takefocus=not self._disabled)

    def state(self, statespec=None):
        if statespec:
            for item in statespec:
                if item in ('disabled', '!disabled'):
                    self._disabled = item == 'disabled'
            self.configure_cursor()
            self._draw()
        return ('disabled',) if self._disabled else ()

    def instate(self, statespec, callback=None):
        matches = all((item == 'disabled') == self._disabled for item in statespec if item in ('disabled', '!disabled'))
        if matches and callback:
            callback()
        return matches

    def _draw(self):
        try:
            on = bool(self.variable.get())
        except tk.TclError:
            return
        self.delete('all')
        width, height, radius = self.WIDTH, self.HEIGHT, self.HEIGHT / 2
        if self._disabled:
            track = '#3d3966' if on else SURFACE_2
            outline = '#3d3966' if on else BORDER
            knob = '#7c7a9a' if on else '#4d5566'
        else:
            track = ACCENT if on else SURFACE_2
            outline = ACCENT if on else '#3a4356'
            knob = '#ffffff' if on else MUTED
        self.create_oval(0, 0, height, height, fill=track, outline=outline)
        self.create_oval(width - height, 0, width, height, fill=track, outline=outline)
        self.create_rectangle(radius, 0, width - radius, height, fill=track, outline=track)
        self.create_line(radius, 0, width - radius, 0, fill=outline)
        self.create_line(radius, height - 1, width - radius, height - 1, fill=outline)
        knob_x = width - height + 3 if on else 3
        self.create_oval(knob_x, 3, knob_x + height - 6, height - 3, fill=knob, outline=knob)


class LauncherView:
    def __init__(self, app):
        self.app, self.root = app, app.root
        self.locked = False
        self.fields = {}
        self.field_pages = {}
        self.secrets = []
        self.controls = []
        self.nav_buttons = {}
        self.nav_indicators = {}
        self.pages = {}
        self.page = 'home'
        self.session_state = 'stopped'
        self.notice_after = None
        self.scroll_after = None
        self.display_family = display_font()
        self.text_family = text_font()
        self.mode_text = tk.StringVar()
        self.destination_text = tk.StringVar()
        self.session_text = tk.StringVar(value='Not running')
        self.session_detail = tk.StringVar()
        self.saved_text = tk.StringVar(value='Settings stay on this PC')
        self.spotify_badge = tk.StringVar()
        self.link_summary = tk.StringVar(value='Start the widget to generate your overlay links.')
        self.checklist_details = {name: tk.StringVar() for name in ('source', 'destination', 'spotify')}
        self.checklist_dots = {}
        app.status = tk.StringVar(value='Preview needs no accounts. Your controls stay private.')
        app.spotify_status = tk.StringVar(value='Use your own developer app. No credentials are included with Live Widget.')
        app.urls = {name: tk.StringVar() for name in LINK_NAMES}
        app.link_buttons = []
        self.root.title('Live Widget')
        self.root.configure(background=BACKGROUND)
        self.root.geometry(initial_window_geometry(self.root))
        self.root.minsize(900, 620)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.option_add('*Font', (self.text_family, 10))
        self.icon = tk.PhotoImage(data=base64.b64encode(icon_png(64)))
        self.root.iconphoto(True, self.icon)
        self._styles()
        self._sidebar()
        self._workspace()
        self._home_page()
        self._setup_page()
        self._overlays_page()
        self._connections_page()
        self._preferences_page()
        self._footer()
        app.configuration_controls = self.controls
        self.show_page('home')
        self.refresh_settings()
        self.set_active(False)
        self.set_session('stopped')
        self.root.bind('<MouseWheel>', self._mousewheel, add='+')
        self.root.bind('<Control-s>', lambda event: self._shortcut(app.save))
        self.root.bind('<Control-Return>', lambda event: self._shortcut(app.start))
        self.root.bind('<FocusIn>', self._focus_changed, add='+')

    # ── styling helpers ───────────────────────────────────────────────────
    def _font(self, size=10, bold=False, display=False):
        return (self.display_family if display else self.text_family, size, 'bold' if bold else 'normal')

    def _styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=self._font(), background=SURFACE, foreground=TEXT)
        style.configure('TEntry', fieldbackground=INPUT, foreground=TEXT, insertcolor=ACCENT,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=(11, 10))
        style.map('TEntry', bordercolor=[('invalid', ERROR), ('focus', ACCENT)],
                  fieldbackground=[('disabled', SURFACE), ('readonly', INPUT)],
                  foreground=[('disabled', MUTED), ('readonly', TEXT)])
        style.configure('TButton', background=SURFACE_2, foreground=TEXT, borderwidth=1, bordercolor='#313a4d',
                        lightcolor=SURFACE_2, darkcolor=SURFACE_2, padding=(15, 10), font=self._font(bold=True),
                        focuscolor=ACCENT)
        style.map('TButton', background=[('disabled', SURFACE), ('pressed', '#2b3447'), ('active', '#242c3d')],
                  foreground=[('disabled', '#6f7a90')], bordercolor=[('focus', ACCENT), ('disabled', BORDER)])
        style.configure('Primary.TButton', background=ACCENT, foreground=ACCENT_TEXT, bordercolor=ACCENT,
                        lightcolor=ACCENT, darkcolor=ACCENT, padding=(21, 11), focuscolor=ACCENT_TEXT)
        style.map('Primary.TButton', background=[('disabled', '#3d3966'), ('pressed', '#7466e6'), ('active', '#a396ff')],
                  foreground=[('disabled', '#9b95c4')], bordercolor=[('focus', TEXT), ('disabled', '#3d3966')])
        style.configure('Stop.TButton', background=ERROR_DARK, foreground=ERROR, bordercolor='#5a3040',
                        lightcolor=ERROR_DARK, darkcolor=ERROR_DARK, padding=(21, 11), focuscolor=ERROR)
        style.map('Stop.TButton', background=[('disabled', '#2a1c24'), ('pressed', '#4a2a3a'), ('active', '#452838')],
                  foreground=[('disabled', '#8a6470')], bordercolor=[('focus', TEXT), ('disabled', '#3a2230')])
        style.configure('Quiet.TButton', background=SURFACE, bordercolor=BORDER, padding=(12, 8))
        style.layout('Choice.TRadiobutton', [('Radiobutton.padding', {'sticky': 'nswe', 'children': [
            ('Radiobutton.focus', {'sticky': 'nswe', 'children': [
                ('Radiobutton.label', {'sticky': 'nswe'})]})]})])
        style.configure('Choice.TRadiobutton', background=SURFACE_2, foreground=MUTED, borderwidth=1,
                        bordercolor=BORDER, relief='solid', padding=(12, 15), anchor='center', justify='center',
                        font=self._font(bold=True), focuscolor=ACCENT)
        style.map('Choice.TRadiobutton', background=[('selected', ACCENT_DARK), ('active', '#20273a')],
                  foreground=[('disabled', '#6f7a90'), ('selected', TEXT), ('active', TEXT)],
                  bordercolor=[('selected', ACCENT)])
        style.configure('Vertical.TScrollbar', background=BORDER, troughcolor=BACKGROUND, borderwidth=0,
                        arrowcolor=MUTED, lightcolor=BORDER, darkcolor=BORDER, width=10)
        style.map('Vertical.TScrollbar', background=[('active', '#3a4356'), ('!active', BORDER)],
                  arrowcolor=[('active', TEXT), ('!active', MUTED)])
        style.configure('Session.Horizontal.TProgressbar', troughcolor=SIDEBAR, background=ACCENT,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

    def _label(self, parent, text='', color=TEXT, size=10, bold=False, variable=None, display=False):
        return tk.Label(parent, text=text, textvariable=variable, background=parent.cget('background'),
                        foreground=color, font=self._font(size, bold, display), anchor='w', justify='left', borderwidth=0)

    def _paragraph(self, parent, text='', variable=None, color=MUTED, size=10):
        label = self._label(parent, text, color=color, variable=variable, size=size)
        label.configure(wraplength=560)
        label.pack(fill='x', pady=(5, 0))
        label.bind('<Configure>', lambda event: label.configure(wraplength=max(180, event.width - 4)))
        return label

    def _button(self, parent, text, command, primary=False, quiet=False, stop=False):
        style = 'Primary.TButton' if primary else 'Stop.TButton' if stop else 'Quiet.TButton' if quiet else 'TButton'
        return ttk.Button(parent, text=text, command=command, style=style, cursor='hand2')

    def _dot(self, parent, color=MUTED, size=10):
        dot = tk.Canvas(parent, width=size, height=size, background=parent.cget('background'),
                        highlightthickness=0, borderwidth=0)
        dot.create_oval(1, 1, size - 1, size - 1, fill=color, outline=color, tags='dot')
        return dot

    @staticmethod
    def _recolor(dot, color):
        dot.itemconfigure('dot', fill=color, outline=color)

    # ── chrome ────────────────────────────────────────────────────────────
    def _sidebar(self):
        sidebar = tk.Frame(self.root, background=SIDEBAR, width=232)
        sidebar.grid(row=0, column=0, rowspan=2, sticky='nsew')
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(2, weight=1)
        brand = tk.Frame(sidebar, background=SIDEBAR)
        brand.grid(row=0, column=0, sticky='ew', padx=22, pady=(26, 28))
        self.brand_icon = tk.PhotoImage(data=base64.b64encode(icon_png(40)))
        row = tk.Frame(brand, background=SIDEBAR)
        row.pack(anchor='w', fill='x')
        tk.Label(row, image=self.brand_icon, background=SIDEBAR).pack(side='left')
        names = tk.Frame(row, background=SIDEBAR)
        names.pack(side='left', padx=(12, 0))
        self._label(names, 'Live Widget', size=15, bold=True, display=True).pack(anchor='w')
        self._label(names, 'Stream companion', color=MUTED, size=9).pack(anchor='w')
        navigation = tk.Frame(sidebar, background=SIDEBAR)
        navigation.grid(row=1, column=0, sticky='ew', padx=12)
        for name, (title, heading, description) in PAGES.items():
            item = tk.Frame(navigation, background=SIDEBAR)
            item.pack(fill='x', pady=2)
            indicator = tk.Frame(item, background=SIDEBAR, width=3)
            indicator.pack(side='left', fill='y')
            button = tk.Button(item, text=title, anchor='w', command=lambda page=name: self.show_page(page),
                               font=self._font(bold=True), padx=13, pady=11, relief='flat', borderwidth=0,
                               background=SIDEBAR, foreground=MUTED, activebackground='#1a1c2e', activeforeground=TEXT,
                               highlightthickness=1, highlightbackground=SIDEBAR, highlightcolor=ACCENT, cursor='hand2')
            button.pack(side='left', fill='x', expand=True)
            self.nav_buttons[name] = button
            self.nav_indicators[name] = (item, indicator)
        bottom = tk.Frame(sidebar, background=SIDEBAR)
        bottom.grid(row=3, column=0, sticky='ew', padx=22, pady=22)
        self.session_pill = tk.Frame(bottom, background=SURFACE_2, padx=12, pady=9,
                                     highlightthickness=1, highlightbackground=BORDER)
        self.session_pill.pack(fill='x')
        self.session_dot = self._dot(self.session_pill, MUTED)
        self.session_dot.pack(side='left')
        self._label(self.session_pill, variable=self.session_text, size=10, bold=True).pack(side='left', padx=(9, 0))
        self.data_folder_button = self._button(bottom, 'Logs & settings folder', self.app.open_data_folder, quiet=True)
        self.data_folder_button.pack(fill='x', pady=(12, 0))

    def _workspace(self):
        workspace = tk.Frame(self.root, background=BACKGROUND)
        workspace.grid(row=0, column=1, sticky='nsew')
        heading = tk.Frame(workspace, background=BACKGROUND)
        heading.pack(fill='x', padx=30, pady=(28, 16))
        self.heading = self._label(heading, '', size=22, bold=True, display=True)
        self.heading.pack(anchor='w')
        self.description = self._paragraph(heading)
        self.notice_frame = tk.Frame(workspace, background=ACCENT_DARK, padx=13, pady=10)
        self.notice = self._label(self.notice_frame, color=ACCENT)
        self.notice.configure(wraplength=650)
        self.notice.pack(fill='x')
        self.notice.bind('<Configure>', lambda event: self.notice.configure(wraplength=max(200, event.width - 4)))
        self.scroller = tk.Frame(workspace, background=BACKGROUND)
        self.scroller.pack(fill='both', expand=True, padx=(30, 16), pady=(0, 20))
        self.canvas = tk.Canvas(self.scroller, background=BACKGROUND, borderwidth=0, highlightthickness=0,
                                yscrollincrement=20)
        self.scrollbar = ttk.Scrollbar(self.scroller, orient='vertical', command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y', padx=(10, 0))
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=self._scroll_position)
        self.content = tk.Frame(self.canvas, background=BACKGROUND)
        self.content.columnconfigure(0, weight=1)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content, anchor='nw')
        self.canvas.bind('<Configure>', self._resize_content)
        self.content.bind('<Configure>', lambda event: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        for name in PAGES:
            page = tk.Frame(self.content, background=BACKGROUND)
            page.columnconfigure(0, weight=1)
            self.pages[name] = page

    def _card(self, page, title, caption=None):
        border = tk.Frame(page, background=BORDER, padx=1, pady=1)
        border.pack(fill='x', pady=(0, 14))
        body = tk.Frame(border, background=SURFACE, padx=21, pady=19)
        body.pack(fill='both', expand=True)
        self._label(body, title, size=12, bold=True, display=True).pack(anchor='w')
        if caption:
            self._paragraph(body, caption)
        return body

    def _field(self, parent, title, name, hint='', secret=False, page='setup'):
        group = tk.Frame(parent, background=SURFACE)
        group.pack(fill='x', pady=(15, 0))
        self._label(group, title, size=9, bold=True).pack(anchor='w', pady=(0, 7))
        row = tk.Frame(group, background=SURFACE)
        row.pack(fill='x')
        entry = ttk.Entry(row, textvariable=self.app.variables[name], show='*' if secret else '')
        entry.pack(side='left', fill='x', expand=True)
        entry.bind('<FocusIn>', lambda event: self.ensure_visible(entry), add='+')
        self.controls.append((entry, 'normal'))
        self.fields[name] = entry
        self.field_pages[name] = page
        if secret:
            toggle = self._button(row, 'Show', lambda: self._toggle_secret(entry, toggle), quiet=True)
            toggle.configure(width=6)
            toggle.pack(side='left', padx=(8, 0))
            self.secrets.append((entry, toggle))
        if hint:
            self._paragraph(group, hint, size=9)
        return group

    def _choices(self, parent, name, choices):
        row = tk.Frame(parent, background=SURFACE)
        row.pack(fill='x', pady=(16, 0))
        for column, (value, title) in enumerate(choices):
            row.columnconfigure(column, weight=1, uniform=name)
            choice = ttk.Radiobutton(row, text=title, variable=self.app.variables[name], value=value,
                                     style='Choice.TRadiobutton', cursor='hand2', takefocus=True)
            choice.grid(row=0, column=column, sticky='ew', padx=(0 if column == 0 else 8, 0))
            self.controls.append((choice, 'normal'))
        return row

    def _switch(self, parent, title, name, hint=''):
        row = tk.Frame(parent, background=parent.cget('background'))
        row.pack(fill='x', pady=(14, 0))
        switch = Switch(row, self.app.variables[name], background=row.cget('background'))
        switch.pack(side='left')
        label = self._label(row, title)
        label.pack(side='left', padx=(12, 0))
        label.configure(cursor='hand2')
        label.bind('<Button-1>', lambda event: switch.toggle())
        self.controls.append((switch, 'normal'))
        if hint:
            self._paragraph(parent, hint, size=9)
        return switch

    _check = _switch

    def _link_row(self, parent, name, background=SURFACE):
        row = tk.Frame(parent, background=background)
        row.pack(fill='x')
        entry = ttk.Entry(row, textvariable=self.app.urls[name], state='readonly')
        entry.pack(side='left', fill='x', expand=True)
        entry.bind('<FocusIn>', lambda event, control=entry: self.ensure_visible(control), add='+')
        for title, command in (
            ('Copy', lambda label=name: self.app.copy(self.app.urls[label].get(), label + ' link')),
            ('Open', lambda label=name: self.app.open_url(self.app.urls[label].get())),
        ):
            button = self._button(row, title, command, quiet=True)
            button.configure(width=6, state='disabled')
            button.pack(side='left', padx=(8, 0))
            self.app.link_buttons.append(button)
        return row

    # ── pages ─────────────────────────────────────────────────────────────
    def _home_page(self):
        page = self.pages['home']
        session = self._card(page, 'Your session')
        headline = tk.Frame(session, background=SURFACE)
        headline.pack(fill='x', pady=(12, 0))
        self.session_headline_dot = self._dot(headline, MUTED, size=12)
        self.session_headline_dot.pack(side='left', pady=(4, 0))
        self.session_headline = self._label(headline, 'Not running', size=16, bold=True, display=True)
        self.session_headline.pack(side='left', padx=(10, 0))
        self._paragraph(session, variable=self.session_detail)
        self._paragraph(session, variable=self.app.status, size=9)
        self.home_action = self._button(session, 'Start preview', self._home_action_clicked, primary=True)
        self.home_action.pack(anchor='w', pady=(16, 0))
        self.home_links = tk.Frame(session, background=SURFACE)
        for name in LINK_NAMES:
            self._label(self.home_links, name.upper(), color=MUTED, size=8, bold=True).pack(anchor='w', pady=(14, 6))
            self._link_row(self.home_links, name)

        checklist = self._card(page, 'Set-up checklist', 'Everything here can be changed later. Preview works with nothing configured.')
        rows = (('source', 'Chat source', 'setup'), ('destination', 'Overlay destination', 'setup'),
                ('spotify', 'Spotify', 'connections'))
        for key, title, target in rows:
            row = tk.Frame(checklist, background=SURFACE)
            row.pack(fill='x', pady=(14, 0))
            dot = self._dot(row, MUTED)
            dot.pack(side='left', pady=(5, 0))
            self.checklist_dots[key] = dot
            text = tk.Frame(row, background=SURFACE)
            text.pack(side='left', fill='x', expand=True, padx=(10, 12))
            self._label(text, title, size=10, bold=True).pack(anchor='w')
            self._label(text, variable=self.checklist_details[key], color=MUTED, size=9).pack(anchor='w', pady=(2, 0))
            self._button(row, 'Go to', lambda target=target: self.show_page(target), quiet=True).pack(side='right')

        tips = self._card(page, 'Adding overlays to OBS or TikTok Studio')
        self._paragraph(tips, '1. Start the widget, then open Overlay links.\n'
                              '2. In OBS add a Browser source and paste a link. Use Public HTTPS for TikTok Studio.\n'
                              '3. Keep the control panel in your own browser and off-stream.')

    def _setup_page(self):
        page = self.pages['setup']
        self.setup_main = tk.Frame(page, background=BACKGROUND)
        self.setup_side = tk.Frame(page, background=BACKGROUND)
        self.setup_main.grid(row=0, column=0, sticky='new')
        self.setup_side.grid(row=1, column=0, sticky='new')
        source = self._card(self.setup_main, 'Chat source', 'Start in Preview to try your overlays without connecting a live account.')
        self._choices(source, 'CHAT_SOURCE', (('preview', 'Preview\nTry it locally'), ('tiktok', 'TikTok\nLive chat'),
                                              ('twitch', 'Twitch\nLive chat'), ('both', 'Both\nOne widget')))
        self.channel_hint = self._paragraph(source, '')
        self.channel_hint.pack_configure(pady=(15, 0))
        self.tiktok_field = self._field(source, 'TikTok username', 'TIKTOK_USER', 'Your handle, with or without @.')
        self.twitch_field = self._field(source, 'Twitch channel', 'TWITCH_CHANNEL', 'The channel you stream to, not its URL.')
        delivery = self._card(self.setup_main, 'Overlay destination')
        self._choices(delivery, 'PUBLIC_TUNNEL', ((False, 'Local / OBS\nOnly this computer'), (True, 'Public HTTPS\nTikTok Studio')))
        self.delivery_hint = self._paragraph(delivery)
        self.delivery_hint.pack_configure(pady=(14, 0))
        controls = self._card(self.setup_side, 'Private controls', 'Your generated password unlocks the control panel. It is never part of an overlay link.')
        self._field(controls, 'Control panel password', 'CONTROL_PASSWORD', secret=True)
        self._button(controls, 'Copy control password', lambda: self.app.copy(self.app.variables['CONTROL_PASSWORD'].get(), 'Control password'), quiet=True).pack(anchor='w', pady=(13, 0))
        next_steps = self._card(self.setup_side, 'What happens next')
        self._paragraph(next_steps, '1. Start the widget from the footer or Home.\n2. Copy an overlay link.\n3. Add it as a browser source.')
        self._button(next_steps, 'View overlay links', lambda: self.show_page('overlays'), quiet=True).pack(anchor='w', pady=(14, 0))

    def _overlays_page(self):
        page = self.pages['overlays']
        intro = tk.Frame(page, background=BACKGROUND)
        intro.pack(fill='x', pady=(0, 17))
        self._paragraph(intro, variable=self.link_summary, color=ACCENT)
        self.link_kinds = {}
        self.link_hints = {}
        captions = {
            'Skip overlay': 'Show your audience the skip vote and, if enabled, the song request list.',
            'Queue overlay': 'Now playing and up next, with album art, as a separate browser source.',
            'Control panel': 'Private workspace for you and your moderators.',
        }
        for name, caption in captions.items():
            card = self._card(page, name, caption)
            kind = self._label(card, 'AVAILABLE AFTER START' if name != 'Control panel' else 'PRIVATE / LOCAL ONLY',
                               color=MUTED if name != 'Control panel' else AMBER, size=8, bold=True)
            kind.pack(anchor='w', pady=(12, 6))
            self.link_kinds[name] = kind
            self._link_row(card, name)
            self.link_hints[name] = self._paragraph(card, LINK_HINTS[name], size=9)
            if name == 'Control panel':
                self._button(card, 'Copy control password', lambda: self.app.copy(self.app.variables['CONTROL_PASSWORD'].get(), 'Control password'), quiet=True).pack(anchor='w', pady=(12, 0))

    def _connections_page(self):
        page = self.pages['connections']
        spotify = self._card(page, 'Spotify', 'Let viewer requests join your playback queue. Preview mode never controls playback.')
        self._label(spotify, variable=self.spotify_badge, color=ACCENT, size=8, bold=True).pack(anchor='w', pady=(12, 0))
        if PUBLIC_CLIENT_ID:
            self._paragraph(spotify, 'Connect your Spotify account in one click. No developer credentials are required.')
        else:
            self._paragraph(spotify, 'Enter credentials for your own Spotify developer app, or configure a public app client ID before packaging.')
        instruction = tk.Frame(spotify, background=INPUT, padx=14, pady=12)
        instruction.pack(fill='x', pady=(14, 0))
        self._paragraph(instruction, '1. Open your developer app.  2. Register this redirect URI.  3. Connect below.')
        row = tk.Frame(instruction, background=INPUT)
        row.pack(fill='x', pady=(9, 0))
        self.redirect_uri = tk.StringVar(value='http://127.0.0.1:8888/callback')
        ttk.Entry(row, textvariable=self.redirect_uri, state='readonly').pack(side='left', fill='x', expand=True)
        self._button(row, 'Copy URI', lambda: self.app.copy(self.redirect_uri.get(), 'Redirect URI'), quiet=True).pack(side='left', padx=(8, 0))
        self._button(spotify, 'Open Spotify developer dashboard', lambda: self.app.open_url('https://developer.spotify.com/dashboard'), quiet=True).pack(anchor='w', pady=(13, 0))
        if not PUBLIC_CLIENT_ID:
            self._field(spotify, 'Client ID', 'SPOTIFY_CLIENT_ID', page='connections')
            self._field(spotify, 'Client secret', 'SPOTIFY_CLIENT_SECRET', secret=True, page='connections')
        actions = tk.Frame(spotify, background=SURFACE)
        actions.pack(fill='x', pady=(16, 0))
        self.app.connect_button = self._button(actions, 'Connect Spotify', self.app.connect_spotify, primary=True)
        self.app.connect_button.pack(side='left')
        self.cancel_button = self._button(actions, 'Cancel sign-in', self.app.cancel_spotify, quiet=True)
        self.cancel_button.pack(side='left', padx=(10, 0))
        self.cancel_button.configure(state='disabled')
        self.oauth_progress = ttk.Progressbar(spotify, mode='indeterminate', style='Session.Horizontal.TProgressbar')
        self._paragraph(spotify, variable=self.app.spotify_status)
        self.advanced_button = self._button(spotify, '+ Advanced Spotify settings', self.toggle_advanced, quiet=True)
        self.advanced_button.pack(anchor='w', pady=(16, 0))
        self.advanced = tk.Frame(spotify, background=SURFACE)
        self.advanced_visible = False
        self._field(self.advanced, 'Refresh token', 'SPOTIFY_REFRESH_TOKEN',
                    'Filled in after sign-in. You may also paste an existing token.', secret=True, page='connections')
        self._field(self.advanced, 'Device ID (optional)', 'SPOTIFY_DEVICE_ID', page='connections')
        twitch = self._card(page, 'Twitch authentication', 'Optional. Leave these blank to use the existing anonymous chat connection.')
        self._field(twitch, 'Bot username', 'TWITCH_BOT_USERNAME', page='connections')
        self._field(twitch, 'OAuth token', 'TWITCH_OAUTH_TOKEN', secret=True, page='connections')

    def _preferences_page(self):
        page = self.pages['preferences']
        voting = self._card(page, 'Voting & moderation', 'Control how your audience requests songs and votes to skip.')
        self._switch(voting, 'Adapt the skip threshold to chat activity', 'ADAPTIVE_SKIP_THRESHOLD_ENABLED')
        self._field(voting, 'Fixed skip vote threshold', 'SKIP_THRESHOLD',
                    'Used only when automatic adaptation is off.', page='preferences')
        self._field(voting, 'Moderator IDs', 'MOD_LIST', 'Comma-separated IDs, not display names.', page='preferences')
        startup = self._card(page, 'Startup & local server')
        self._switch(startup, 'Open the control panel in my browser after starting', 'AUTO_OPEN')
        self._field(startup, 'Local port', 'PORT', 'Default: 5000. Choose another port if a different app is using it.', page='preferences')
        storage = self._card(page, 'Your workspace', 'Settings, logs, and queue state live outside the EXE, so replacing the app keeps your setup.')
        self._paragraph(storage, str(self.app.directory))
        self._button(storage, 'Open logs & settings folder', self.app.open_data_folder, quiet=True).pack(anchor='w', pady=(14, 0))
        self._paragraph(storage, 'Passwords and tokens are protected for your Windows account. Never share your settings or logs.')

    def _footer(self):
        footer = tk.Frame(self.root, background=SIDEBAR, highlightbackground=BORDER, highlightthickness=1)
        footer.grid(row=1, column=1, sticky='ew')
        self.progress = ttk.Progressbar(footer, mode='indeterminate', style='Session.Horizontal.TProgressbar')
        body = tk.Frame(footer, background=SIDEBAR, padx=24, pady=17)
        body.pack(fill='x')
        self.footer_actions = tk.Frame(body, background=SIDEBAR)
        self.footer_actions.pack(side='right', padx=(16, 0))
        self.app.save_button = self._button(self.footer_actions, 'Save settings', self.app.save, quiet=True)
        self.app.save_button.pack(side='left', padx=(0, 8))
        self.app.stop_button = self._button(self.footer_actions, 'Stop', self.app.stop, stop=True)
        self.app.start_button = self._button(self.footer_actions, 'Start preview', self.app.start, primary=True)
        self.app.start_button.pack(side='left')
        status = tk.Frame(body, background=SIDEBAR)
        status.pack(side='left', fill='both', expand=True)
        self.session_title = self._label(status, 'Ready to start', bold=True)
        self.session_title.pack(anchor='w')
        self._paragraph(status, variable=self.app.status)
        self.saved_label = self._label(status, variable=self.saved_text, color=MUTED, size=8)
        self.saved_label.pack(anchor='w', pady=(6, 0))

    # ── state ─────────────────────────────────────────────────────────────
    def show_page(self, name):
        if name not in self.pages:
            return
        self.page = name
        for page_name, page in self.pages.items():
            selected = page_name == name
            if selected:
                page.grid(row=0, column=0, sticky='ew')
            else:
                page.grid_remove()
            item, indicator = self.nav_indicators[page_name]
            item.configure(background=ACCENT_DARK if selected else SIDEBAR)
            indicator.configure(background=ACCENT if selected else SIDEBAR)
            self.nav_buttons[page_name].configure(background=ACCENT_DARK if selected else SIDEBAR,
                                                  foreground=TEXT if selected else MUTED,
                                                  highlightbackground=ACCENT_DARK if selected else SIDEBAR)
        title, heading, description = PAGES[name]
        self.heading.configure(text=heading)
        self.description.configure(text=description)
        self.canvas.yview_moveto(0)
        self.mask_secrets()

    def _source_label(self, source):
        return {'preview': 'Preview session', 'tiktok': 'TikTok chat', 'twitch': 'Twitch chat', 'both': 'TikTok + Twitch'}.get(source, 'Choose a source')

    def refresh_settings(self):
        variables = self.app.variables
        source = variables['CHAT_SOURCE'].get()
        self.mode_text.set(self._source_label(source))
        public = variables['PUBLIC_TUNNEL'].get()
        self.destination_text.set('Public HTTPS overlays' if public else 'Local overlays / OBS')
        self.session_detail.set(f'{self.mode_text.get()}  ·  {self.destination_text.get()}')
        self.delivery_hint.configure(
            text='Creates an internet-accessible link through Cloudflare. Keep your control password private.' if public
            else 'No tunnel needed. Your overlays are available only on this computer.')
        self.channel_hint.configure(text='A safe place to try things. No live chat connections or Spotify playback.' if source == 'preview'
                                    else 'Enter the account you will stream from. You can start the widget before going live.')
        for group, visible in ((self.tiktok_field, source in ('tiktok', 'both')), (self.twitch_field, source in ('twitch', 'both'))):
            if visible:
                group.pack(fill='x', pady=(15, 0))
            else:
                group.pack_forget()
        for entry in self.fields.values():
            entry.state(['!invalid'])
        self.fields['SKIP_THRESHOLD'].configure(state='disabled' if self.locked or variables['ADAPTIVE_SKIP_THRESHOLD_ENABLED'].get() else 'normal')
        configured = bool(variables['SPOTIFY_REFRESH_TOKEN'].get().strip()) and (
            bool(PUBLIC_CLIENT_ID) or all(variables[name].get().strip() for name in ('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET'))
        )
        self.spotify_badge.set('CREDENTIALS ENTERED' if configured else 'OPTIONAL / NOT CONFIGURED')
        self._refresh_checklist(source, public, configured)
        if not self.app.running and not self.app.busy and self.app.process.server is None:
            text = 'Start preview' if source == 'preview' else 'Start widget'
            self.app.start_button.configure(text=text)
            self.home_action.configure(text=text)
            self.app.status.set('Preview needs no accounts. Your controls stay private.' if source == 'preview'
                                else 'Start your widget, then go live on your selected channel.')
        dirty = self.app.values() != self.app.saved_settings
        self.saved_text.set('Unsaved changes  /  Ctrl+S to save' if dirty else 'Settings stay on this PC')
        self.saved_label.configure(foreground=AMBER if dirty else MUTED)

    def _refresh_checklist(self, source, public, spotify_configured):
        variables = self.app.variables
        accounts = []
        if source in ('tiktok', 'both'):
            handle = variables['TIKTOK_USER'].get().strip().lstrip('@')
            accounts.append('@' + handle if handle else 'TikTok username missing')
        if source in ('twitch', 'both'):
            channel = variables['TWITCH_CHANNEL'].get().strip().lstrip('#')
            accounts.append('#' + channel if channel else 'Twitch channel missing')
        missing = any('missing' in item for item in accounts)
        detail = self._source_label(source) + ('  ·  ' + ', '.join(accounts) if accounts else '  ·  no account needed')
        self.checklist_details['source'].set(detail)
        self._recolor(self.checklist_dots['source'], AMBER if missing else SUCCESS)
        self.checklist_details['destination'].set('Public HTTPS via Cloudflare for TikTok Studio' if public else 'Local overlays for OBS on this computer')
        self._recolor(self.checklist_dots['destination'], SUCCESS)
        self.checklist_details['spotify'].set('Connected with your own developer app' if spotify_configured else 'Optional  ·  not connected')
        self._recolor(self.checklist_dots['spotify'], SUCCESS if spotify_configured else MUTED)

    def set_active(self, active):
        self.locked = active
        for control, initial_state in self.controls:
            control.configure(state='disabled' if active else initial_state)
        for button in (self.app.start_button, self.app.save_button, self.app.connect_button):
            button.configure(state='disabled' if active else 'normal')
        self.app.stop_button.configure(state='normal' if self.app.process.server is not None and not self.app.busy else 'disabled')
        self.refresh_settings()
        self._sync_home_action()

    def set_session(self, state):
        self.session_state = state
        pill, color, title = SESSION_STATES[state]
        if state == 'running':
            pill = 'Running  ·  ' + ('Preview' if self.app.variables['CHAT_SOURCE'].get() == 'preview' else 'Live')
        self.session_text.set(pill)
        self._recolor(self.session_dot, color)
        self._recolor(self.session_headline_dot, color)
        self.session_pill.configure(background=SUCCESS_DARK if state == 'running' else SURFACE_2,
                                    highlightbackground=SUCCESS if state == 'running' else BORDER)
        for child in self.session_pill.winfo_children():
            child.configure(background=self.session_pill.cget('background'))
        self.session_headline.configure(text=pill, foreground=color if state != 'stopped' else TEXT)
        self.session_title.configure(text=title, foreground=color if state != 'stopped' else TEXT)
        self.progress.stop()
        self.progress.pack_forget()
        if state in ('starting', 'stopping'):
            self.progress.pack(fill='x', side='top', before=self.progress.master.winfo_children()[1])
            self.progress.start(15)
        source_text = 'Start preview' if self.app.variables['CHAT_SOURCE'].get() == 'preview' else 'Start widget'
        self.app.start_button.configure(text='Starting...' if state == 'starting' else source_text)
        self.app.stop_button.configure(text='Stopping...' if state == 'stopping' else 'Stop')
        show_stop = state in ('running', 'stopping')
        if show_stop:
            self.app.start_button.pack_forget()
            if not self.app.stop_button.winfo_manager():
                self.app.stop_button.pack(side='left')
        else:
            self.app.stop_button.pack_forget()
            if not self.app.start_button.winfo_manager():
                self.app.start_button.pack(side='left')
        self._sync_home_action()

    def _sync_home_action(self):
        show_stop = self.session_state in ('running', 'stopping')
        source_button = self.app.stop_button if show_stop else self.app.start_button
        self.home_action.configure(text=str(source_button.cget('text')), style='Stop.TButton' if show_stop else 'Primary.TButton',
                                   state='disabled' if source_button.instate(['disabled']) else 'normal')

    def _home_action_clicked(self):
        if self.session_state in ('running', 'stopping'):
            self.app.stop()
        else:
            self.app.start()

    def links_ready(self, ready, public=False):
        for button in self.app.link_buttons:
            button.configure(state='normal' if ready else 'disabled')
        self.link_summary.set('Paste an overlay URL into a browser source. Keep the control panel off-stream.' if ready
                              else 'Start the widget to generate your overlay links.')
        for name in ('Skip overlay', 'Queue overlay'):
            self.link_kinds[name].configure(text=('PUBLIC HTTPS' if public else 'LOCAL / THIS COMPUTER') if ready else 'AVAILABLE AFTER START',
                                            foreground=SUCCESS if ready else MUTED)
        if ready:
            self.home_links.pack(fill='x', pady=(4, 0))
        else:
            self.home_links.pack_forget()

    def oauth_pending(self, pending):
        self.cancel_button.configure(state='normal' if pending else 'disabled')
        self.app.connect_button.configure(text='Waiting for browser...' if pending else 'Connect Spotify')
        self.oauth_progress.stop()
        self.oauth_progress.pack_forget()
        if pending:
            self.oauth_progress.pack(fill='x', pady=(13, 0), before=self.advanced_button)
            self.oauth_progress.start(15)

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        self.advanced_button.configure(text='- Hide advanced Spotify settings' if self.advanced_visible else '+ Advanced Spotify settings')
        if self.advanced_visible:
            self.advanced.pack(fill='x')
        else:
            self.advanced.pack_forget()
            self.mask_secrets()

    def _toggle_secret(self, entry, button):
        visible = bool(entry.cget('show'))
        entry.configure(show='' if visible else '*')
        button.configure(text='Hide' if visible else 'Show')

    def mask_secrets(self):
        for entry, button in self.secrets:
            entry.configure(show='*')
            button.configure(text='Show')

    def notify(self, text, error=False):
        if self.notice_after:
            self.root.after_cancel(self.notice_after)
            self.notice_after = None
        background = ERROR_DARK if error else ACCENT_DARK
        self.notice_frame.configure(background=background)
        self.notice.configure(text=text, background=background, foreground=ERROR if error else TEXT)
        self.notice_frame.pack(fill='x', padx=30, pady=(0, 13), before=self.scroller)
        if not error:
            self.notice_after = self.root.after(5000, self.clear_notice)

    def clear_notice(self):
        if self.notice_after:
            self.root.after_cancel(self.notice_after)
            self.notice_after = None
        self.notice_frame.pack_forget()

    def show_error(self, text, field=None):
        if field is None:
            for phrase, candidate in (('tiktok', 'TIKTOK_USER'), ('twitch channel', 'TWITCH_CHANNEL'),
                                      ('password', 'CONTROL_PASSWORD'), ('port', 'PORT'),
                                      ('skip_threshold', 'SKIP_THRESHOLD'), ('spotify', 'SPOTIFY_CLIENT_ID')):
                if phrase in text.lower():
                    field = candidate
                    break
        if field in self.fields:
            self.show_page(self.field_pages[field])
            if field in ('SPOTIFY_REFRESH_TOKEN', 'SPOTIFY_DEVICE_ID') and not self.advanced_visible:
                self.toggle_advanced()
            entry = self.fields[field]
            entry.state(['invalid'])
            entry.focus_set()
            if self.scroll_after:
                self.root.after_cancel(self.scroll_after)
            self.scroll_after = self.root.after_idle(lambda: self.ensure_visible(entry))
        self.notify(text, error=True)

    # ── scrolling & layout ────────────────────────────────────────────────
    def ensure_visible(self, control):
        self.scroll_after = None
        if not control.winfo_ismapped():
            return
        top = control.winfo_rooty() - self.content.winfo_rooty()
        viewport_top = self.canvas.canvasy(0)
        viewport_bottom = viewport_top + self.canvas.winfo_height()
        if top < viewport_top or top + control.winfo_height() > viewport_bottom:
            self.canvas.yview_moveto(max(0, top - 45) / max(1, self.content.winfo_height()))

    def _mousewheel(self, event):
        target = self.root.winfo_containing(event.x_root, event.y_root)
        if target is not None and str(target).startswith(str(self.scroller)):
            if self.content.winfo_height() > self.canvas.winfo_height():
                self.canvas.yview_scroll(-int(event.delta / 120), 'units')
                return 'break'

    def _scroll_position(self, first, last):
        self.scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.scrollbar.pack_forget()
        elif not self.scrollbar.winfo_manager():
            self.scrollbar.pack(side='right', fill='y', padx=(10, 0), before=self.canvas)

    def _focus_changed(self, event):
        if str(event.widget).startswith(str(self.content)):
            self.ensure_visible(event.widget)

    def _resize_content(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        if not hasattr(self, 'setup_side'):
            return
        wide = event.width >= 800
        page = self.pages['setup']
        page.columnconfigure(0, weight=2 if wide else 1, minsize=0, uniform='setup' if wide else '')
        page.columnconfigure(1, weight=1 if wide else 0, minsize=270 if wide else 0, uniform='setup' if wide else '')
        self.setup_main.grid_configure(row=0, column=0, padx=(0, 14 if wide else 0))
        self.setup_side.grid_configure(row=0 if wide else 1, column=1 if wide else 0)

    def _shortcut(self, action):
        if not self.locked:
            action()
        return 'break'

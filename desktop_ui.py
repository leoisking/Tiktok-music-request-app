"""Dark, keyboard-accessible presentation layer for the desktop launcher."""

import base64
import tkinter as tk
from tkinter import ttk

from desktop_branding import icon_png


BACKGROUND = '#0c1119'
SIDEBAR = '#101722'
SURFACE = '#161f2c'
INPUT = '#0f1722'
BORDER = '#2b394b'
TEXT = '#edf2f8'
MUTED = '#9cacc1'
ACCENT = '#80ebc5'
ACCENT_DARK = '#193b32'
ERROR = '#ff9aa7'
AMBER = '#f3ce8e'

PAGES = {
    'setup': ('01', 'Stream setup', 'Make it your stream.', 'Choose your chat source and where your overlays will run.'),
    'overlays': ('02', 'Overlay links', 'Your stream, connected.', 'Copy a browser-source link into OBS or TikTok Studio.'),
    'connections': ('03', 'Connections', 'Bring the music.', 'Connect your own accounts. Spotify is completely optional.'),
    'preferences': ('04', 'Preferences', 'The details, your way.', 'Tune voting, moderation, and your local workspace.'),
}


def initial_window_geometry(root):
    width = min(1120, max(900, root.winfo_screenwidth() - 80))
    height = min(820, max(620, root.winfo_screenheight() - 100))
    return f'{width}x{height}'


class LauncherView:
    def __init__(self, app):
        self.app, self.root = app, app.root
        self.locked = False
        self.fields = {}
        self.field_pages = {}
        self.secrets = []
        self.controls = []
        self.nav_buttons = {}
        self.pages = {}
        self.page = 'setup'
        self.session_state = 'stopped'
        self.notice_after = None
        self.scroll_after = None
        self.mode_text = tk.StringVar()
        self.destination_text = tk.StringVar()
        self.saved_text = tk.StringVar(value='Settings stay on this PC')
        self.spotify_badge = tk.StringVar()
        self.link_summary = tk.StringVar(value='Start the widget to generate your overlay links.')
        app.status = tk.StringVar(value='Preview needs no accounts. Your controls stay private.')
        app.spotify_status = tk.StringVar(value='Use your own developer app. No credentials are included with Live Widget.')
        app.urls = {name: tk.StringVar() for name in ('Skip overlay', 'Queue overlay', 'Control panel')}
        app.link_buttons = []
        self.root.title('Live Widget')
        self.root.configure(background=BACKGROUND)
        self.root.geometry(initial_window_geometry(self.root))
        self.root.minsize(900, 620)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.option_add('*Font', ('Segoe UI', 10))
        self.icon = tk.PhotoImage(data=base64.b64encode(icon_png(64)))
        self.root.iconphoto(True, self.icon)
        self._styles()
        self._sidebar()
        self._workspace()
        self._setup_page()
        self._overlays_page()
        self._connections_page()
        self._preferences_page()
        self._footer()
        app.configuration_controls = self.controls
        self.show_page('setup')
        self.refresh_settings()
        self.set_active(False)
        self.root.bind('<MouseWheel>', self._mousewheel, add='+')
        self.root.bind('<Control-s>', lambda event: self._shortcut(app.save))
        self.root.bind('<Control-Return>', lambda event: self._shortcut(app.start))
        self.root.bind('<Configure>', self._resize_root, add='+')
        self.root.bind('<FocusIn>', self._focus_changed, add='+')

    def _styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background=SURFACE, foreground=TEXT)
        style.configure('TEntry', fieldbackground=INPUT, foreground=TEXT, insertcolor=ACCENT,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=(11, 10))
        style.map('TEntry', bordercolor=[('invalid', ERROR), ('focus', ACCENT)],
                  fieldbackground=[('disabled', SURFACE), ('readonly', INPUT)],
                  foreground=[('disabled', MUTED), ('readonly', TEXT)])
        style.configure('TButton', background='#253448', foreground=TEXT, borderwidth=1, bordercolor='#34465e',
                        lightcolor='#253448', darkcolor='#253448', padding=(15, 10), font=('Segoe UI', 10, 'bold'),
                        focuscolor=ACCENT)
        style.map('TButton', background=[('disabled', SURFACE), ('pressed', '#354963'), ('active', '#30445d')],
                  foreground=[('disabled', '#78899f')], bordercolor=[('focus', ACCENT), ('disabled', BORDER)])
        style.configure('Primary.TButton', background=ACCENT, foreground='#0a2119', bordercolor=ACCENT,
                        lightcolor=ACCENT, darkcolor=ACCENT, padding=(21, 11), focuscolor='#163e30')
        style.map('Primary.TButton', background=[('disabled', '#264538'), ('pressed', '#55cfa4'), ('active', '#a1f5d6')],
                  foreground=[('disabled', '#9fbcaf')], bordercolor=[('focus', TEXT), ('disabled', '#264538')])
        style.configure('Quiet.TButton', background=SURFACE, bordercolor=BORDER, padding=(12, 8))
        style.configure('Danger.TButton', foreground=ERROR)
        style.layout('Choice.TRadiobutton', [('Radiobutton.padding', {'sticky': 'nswe', 'children': [
            ('Radiobutton.focus', {'sticky': 'nswe', 'children': [
                ('Radiobutton.label', {'sticky': 'nswe'})]})]})])
        style.configure('Choice.TRadiobutton', background=INPUT, foreground=MUTED, borderwidth=1,
                        relief='solid', padding=(12, 15), anchor='center', justify='center',
                        font=('Segoe UI', 10, 'bold'), focuscolor=ACCENT)
        style.map('Choice.TRadiobutton', background=[('selected', ACCENT_DARK), ('active', '#223144')],
                  foreground=[('disabled', '#83978f'), ('selected', ACCENT), ('active', TEXT)])
        style.configure('TCheckbutton', background=SURFACE, foreground=TEXT, padding=(0, 6),
                        indicatorbackground=INPUT, indicatorforeground=ACCENT, focuscolor=ACCENT)
        style.map('TCheckbutton', background=[('active', SURFACE)], foreground=[('disabled', MUTED)],
                  indicatorbackground=[('selected', ACCENT_DARK), ('disabled', SURFACE)])
        style.configure('Vertical.TScrollbar', background=BORDER, troughcolor=BACKGROUND, borderwidth=0,
                        arrowcolor=MUTED, lightcolor=BORDER, darkcolor=BORDER, width=10)
        style.map('Vertical.TScrollbar', background=[('active', '#40546e'), ('!active', BORDER)],
                  arrowcolor=[('active', TEXT), ('!active', MUTED)])
        style.configure('Session.Horizontal.TProgressbar', troughcolor=SIDEBAR, background=ACCENT,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

    def _label(self, parent, text='', color=TEXT, size=10, bold=False, variable=None):
        label = tk.Label(parent, text=text, textvariable=variable, background=parent.cget('background'),
                         foreground=color, font=('Segoe UI', size, 'bold' if bold else 'normal'),
                         anchor='w', justify='left', borderwidth=0)
        return label

    def _paragraph(self, parent, text='', variable=None, color=MUTED):
        label = self._label(parent, text, color=color, variable=variable)
        label.configure(wraplength=560)
        label.pack(fill='x', pady=(5, 0))
        label.bind('<Configure>', lambda event: label.configure(wraplength=max(180, event.width - 4)))
        return label

    def _button(self, parent, text, command, primary=False, quiet=False):
        style = 'Primary.TButton' if primary else 'Quiet.TButton' if quiet else 'TButton'
        return ttk.Button(parent, text=text, command=command, style=style, cursor='hand2')

    def _sidebar(self):
        sidebar = tk.Frame(self.root, background=SIDEBAR, width=224)
        sidebar.grid(row=0, column=0, rowspan=2, sticky='nsew')
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(2, weight=1)
        brand = tk.Frame(sidebar, background=SIDEBAR)
        brand.grid(row=0, column=0, sticky='ew', padx=23, pady=(30, 35))
        self.brand_icon = tk.PhotoImage(data=base64.b64encode(icon_png(44)))
        tk.Label(brand, image=self.brand_icon, background=SIDEBAR).pack(anchor='w', pady=(0, 14))
        self._label(brand, 'Live Widget', size=19, bold=True).pack(anchor='w')
        self._label(brand, 'YOUR STREAM COMPANION', color=MUTED, size=8).pack(anchor='w', pady=(5, 0))
        navigation = tk.Frame(sidebar, background=SIDEBAR)
        navigation.grid(row=1, column=0, sticky='ew', padx=14)
        for name, (number, title, heading, description) in PAGES.items():
            button = tk.Button(navigation, text=f'{number}   {title}', anchor='w', command=lambda page=name: self.show_page(page),
                               font=('Segoe UI', 10, 'bold'), padx=13, pady=13, relief='flat', borderwidth=0,
                               background=SIDEBAR, foreground=MUTED, activebackground='#20312f', activeforeground=ACCENT,
                               highlightthickness=1, highlightbackground=SIDEBAR, highlightcolor=ACCENT, cursor='hand2')
            button.pack(fill='x', pady=3)
            self.nav_buttons[name] = button
        bottom = tk.Frame(sidebar, background=SIDEBAR)
        bottom.grid(row=3, column=0, sticky='ew', padx=23, pady=24)
        self.sidebar_plan = tk.Frame(bottom, background=SIDEBAR)
        self.sidebar_plan.pack(fill='x')
        self._label(self.sidebar_plan, 'SESSION PLAN', color=MUTED, size=8, bold=True).pack(anchor='w')
        self._label(self.sidebar_plan, variable=self.mode_text, size=11, bold=True).pack(anchor='w', pady=(8, 2))
        self._label(self.sidebar_plan, variable=self.destination_text, color=MUTED, size=9).pack(anchor='w')
        self.sidebar_rule = tk.Frame(bottom, height=1, background=BORDER)
        self.sidebar_rule.pack(fill='x', pady=17)
        self._label(bottom, 'PRIVATE BY DEFAULT', color=ACCENT, size=8, bold=True).pack(anchor='w')
        self._label(bottom, 'Your keys stay on this PC.', color=MUTED, size=9).pack(anchor='w', pady=(6, 15))
        self.data_folder_button = self._button(
            bottom, 'Logs & settings folder', self.app.open_data_folder, quiet=True,
        )
        self.data_folder_button.pack(fill='x')

    def _workspace(self):
        workspace = tk.Frame(self.root, background=BACKGROUND)
        workspace.grid(row=0, column=1, sticky='nsew')
        heading = tk.Frame(workspace, background=BACKGROUND)
        heading.pack(fill='x', padx=30, pady=(27, 18))
        self.badge = tk.Label(heading, text='  NOT RUNNING  ', font=('Segoe UI', 8, 'bold'), padx=10, pady=8,
                              background='#202d3d', foreground=MUTED)
        self.badge.pack(side='right', anchor='n', pady=(4, 0))
        self.eyebrow = self._label(heading, '', color=ACCENT, size=9, bold=True)
        self.eyebrow.pack(anchor='w')
        self.heading = self._label(heading, '', size=25, bold=True)
        self.heading.pack(anchor='w', pady=(10, 7))
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
        self._label(body, title, size=13, bold=True).pack(anchor='w')
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
            self._paragraph(group, hint)
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

    def _check(self, parent, title, name):
        check = ttk.Checkbutton(parent, text=title, variable=self.app.variables[name], cursor='hand2')
        check.pack(anchor='w', pady=(12, 0))
        self.controls.append((check, 'normal'))
        return check

    def _setup_page(self):
        page = self.pages['setup']
        self.setup_main = tk.Frame(page, background=BACKGROUND)
        self.setup_side = tk.Frame(page, background=BACKGROUND)
        self.setup_main.grid(row=0, column=0, sticky='new')
        self.setup_side.grid(row=1, column=0, sticky='new')
        source = self._card(self.setup_main, '01  Choose your chat source', 'Start in Preview to try your overlays without connecting a live account.')
        self._choices(source, 'CHAT_SOURCE', (('preview', 'Preview\nTry it locally'), ('tiktok', 'TikTok\nLive chat'),
                                              ('twitch', 'Twitch\nLive chat'), ('both', 'Both\nOne widget')))
        self.channel_hint = self._paragraph(source, '')
        self.channel_hint.pack_configure(pady=(15, 0))
        self.tiktok_field = self._field(source, 'TikTok username', 'TIKTOK_USER', 'Your handle, with or without @.')
        self.twitch_field = self._field(source, 'Twitch channel', 'TWITCH_CHANNEL', 'The channel you stream to, not its URL.')
        delivery = self._card(self.setup_main, '02  Overlay destination')
        self._choices(delivery, 'PUBLIC_TUNNEL', ((False, 'Local / OBS\nOnly this computer'), (True, 'Public HTTPS\nTikTok Studio')))
        self.delivery_hint = self._paragraph(delivery)
        self.delivery_hint.pack_configure(pady=(14, 0))
        controls = self._card(self.setup_side, '03  Private controls', 'Your generated password unlocks the control panel. It is never part of an overlay link.')
        self._field(controls, 'Control panel password', 'CONTROL_PASSWORD', secret=True)
        self._button(controls, 'Copy control password', lambda: self.app.copy(self.app.variables['CONTROL_PASSWORD'].get(), 'Control password'), quiet=True).pack(anchor='w', pady=(13, 0))
        next_steps = self._card(self.setup_side, 'Once you start')
        self._paragraph(next_steps, '1. Open your control panel.\n2. Copy an overlay link.\n3. Add a browser source.')
        self._button(next_steps, 'View overlay links', lambda: self.show_page('overlays'), quiet=True).pack(anchor='w', pady=(14, 0))

    def _overlays_page(self):
        page = self.pages['overlays']
        intro = tk.Frame(page, background=BACKGROUND)
        intro.pack(fill='x', pady=(0, 17))
        self._paragraph(intro, variable=self.link_summary, color=ACCENT)
        self.link_kinds = {}
        captions = {
            'Skip overlay': 'Show your audience the current skip vote and song request activity.',
            'Queue overlay': 'Display the upcoming songs as a separate browser source.',
            'Control panel': 'Private workspace. Never add this page to your broadcast.',
        }
        for name, caption in captions.items():
            card = self._card(page, name, caption)
            kind = self._label(card, 'AVAILABLE AFTER START' if name != 'Control panel' else 'PRIVATE / LOCAL ONLY',
                               color=MUTED if name != 'Control panel' else AMBER, size=8, bold=True)
            kind.pack(anchor='w', pady=(12, 6))
            self.link_kinds[name] = kind
            row = tk.Frame(card, background=SURFACE)
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
            if name == 'Control panel':
                self._button(card, 'Copy control password', lambda: self.app.copy(self.app.variables['CONTROL_PASSWORD'].get(), 'Control password'), quiet=True).pack(anchor='w', pady=(12, 0))

    def _connections_page(self):
        page = self.pages['connections']
        spotify = self._card(page, 'Spotify', 'Let viewer requests join your playback queue. Preview mode never controls playback.')
        self._label(spotify, variable=self.spotify_badge, color=ACCENT, size=8, bold=True).pack(anchor='w', pady=(12, 0))
        instruction = tk.Frame(spotify, background=INPUT, padx=14, pady=12)
        instruction.pack(fill='x', pady=(14, 0))
        self._paragraph(instruction, '1. Open your developer app.  2. Register this redirect URI.  3. Connect below.')
        row = tk.Frame(instruction, background=INPUT)
        row.pack(fill='x', pady=(9, 0))
        self.redirect_uri = tk.StringVar(value='http://127.0.0.1:8888/callback')
        ttk.Entry(row, textvariable=self.redirect_uri, state='readonly').pack(side='left', fill='x', expand=True)
        self._button(row, 'Copy URI', lambda: self.app.copy(self.redirect_uri.get(), 'Redirect URI'), quiet=True).pack(side='left', padx=(8, 0))
        self._button(spotify, 'Open Spotify developer dashboard', lambda: self.app.open_url('https://developer.spotify.com/dashboard'), quiet=True).pack(anchor='w', pady=(13, 0))
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
        self._check(voting, 'Adapt the skip threshold automatically', 'ADAPTIVE_SKIP_THRESHOLD_ENABLED')
        self._field(voting, 'Fixed skip vote threshold', 'SKIP_THRESHOLD',
                    'Used only when automatic adaptation is off.', page='preferences')
        self._field(voting, 'Moderator IDs', 'MOD_LIST', 'Comma-separated IDs, not display names.', page='preferences')
        startup = self._card(page, 'Startup & local server')
        self._check(startup, 'Open the control panel in my browser after starting', 'AUTO_OPEN')
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
        actions = tk.Frame(body, background=SIDEBAR)
        actions.pack(side='right', padx=(16, 0))
        self.app.save_button = self._button(actions, 'Save settings', self.app.save, quiet=True)
        self.app.save_button.pack(side='left', padx=(0, 8))
        self.app.stop_button = self._button(actions, 'Stop', self.app.stop, quiet=True)
        self.app.stop_button.pack(side='left', padx=(0, 8))
        self.app.start_button = self._button(actions, 'Start preview', self.app.start, primary=True)
        self.app.start_button.pack(side='left')
        status = tk.Frame(body, background=SIDEBAR)
        status.pack(side='left', fill='both', expand=True)
        self.session_title = self._label(status, 'Ready to start', bold=True)
        self.session_title.pack(anchor='w')
        self._paragraph(status, variable=self.app.status)
        self.saved_label = self._label(status, variable=self.saved_text, color=MUTED, size=8)
        self.saved_label.pack(anchor='w', pady=(6, 0))

    def show_page(self, name):
        if name not in self.pages:
            return
        self.page = name
        for page_name, page in self.pages.items():
            if page_name == name:
                page.grid(row=0, column=0, sticky='ew')
            else:
                page.grid_remove()
            selected = page_name == name
            self.nav_buttons[page_name].configure(background=ACCENT_DARK if selected else SIDEBAR,
                                                  foreground=ACCENT if selected else MUTED)
        number, title, heading, description = PAGES[name]
        self.eyebrow.configure(text=f'WORKSPACE  /  {number}  {title.upper()}')
        self.heading.configure(text=heading)
        self.description.configure(text=description)
        self.canvas.yview_moveto(0)
        self.mask_secrets()

    def refresh_settings(self):
        source = self.app.variables['CHAT_SOURCE'].get()
        self.mode_text.set({'preview': 'Preview session', 'tiktok': 'TikTok chat', 'twitch': 'Twitch chat', 'both': 'TikTok + Twitch'}.get(source, 'Choose a source'))
        public = self.app.variables['PUBLIC_TUNNEL'].get()
        self.destination_text.set('Public HTTPS overlays' if public else 'Local overlays / OBS')
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
        self.fields['SKIP_THRESHOLD'].configure(state='disabled' if self.locked or self.app.variables['ADAPTIVE_SKIP_THRESHOLD_ENABLED'].get() else 'normal')
        configured = all(self.app.variables[name].get().strip() for name in ('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN'))
        self.spotify_badge.set('CREDENTIALS ENTERED' if configured else 'OPTIONAL / NOT CONFIGURED')
        if not self.app.running and not self.app.busy and self.app.process.server is None:
            self.app.start_button.configure(text='Start preview' if source == 'preview' else 'Start widget')
            self.app.status.set('Preview needs no accounts. Your controls stay private.' if source == 'preview'
                                else 'Start your widget, then go live on your selected channel.')
        dirty = self.app.values() != self.app.saved_settings
        self.saved_text.set('Unsaved changes  /  Ctrl+S to save' if dirty else 'Settings stay on this PC')
        self.saved_label.configure(foreground=AMBER if dirty else MUTED)

    def set_active(self, active):
        self.locked = active
        for control, initial_state in self.controls:
            control.configure(state='disabled' if active else initial_state)
        for button in (self.app.start_button, self.app.save_button, self.app.connect_button):
            button.configure(state='disabled' if active else 'normal')
        self.app.stop_button.configure(state='normal' if self.app.process.server is not None and not self.app.busy else 'disabled')
        self.refresh_settings()

    def set_session(self, state):
        self.session_state = state
        titles = {'stopped': ('NOT RUNNING', 'Ready to start', MUTED),
                  'starting': ('STARTING', 'Getting your widget ready', AMBER),
                  'running': ('PREVIEW' if self.app.variables['CHAT_SOURCE'].get() == 'preview' else 'RUNNING', 'Widget server running', ACCENT),
                  'stopping': ('STOPPING', 'Closing your session', AMBER)}
        badge, title, color = titles[state]
        self.badge.configure(text=f'  {badge}  ', foreground=color,
                             background=ACCENT_DARK if state == 'running' else '#202d3d')
        self.session_title.configure(text=title, foreground=color if state != 'stopped' else TEXT)
        self.progress.stop()
        self.progress.pack_forget()
        if state in ('starting', 'stopping'):
            self.progress.pack(fill='x', side='top', before=self.progress.master.winfo_children()[1])
            self.progress.start(15)
        self.app.start_button.configure(text='Starting...' if state == 'starting' else 'Widget running' if state == 'running'
                                         else 'Start preview' if self.app.variables['CHAT_SOURCE'].get() == 'preview' else 'Start widget')

    def links_ready(self, ready, public=False):
        for button in self.app.link_buttons:
            button.configure(state='normal' if ready else 'disabled')
        self.link_summary.set('Paste an overlay URL into a browser source. Keep the control panel off-stream.' if ready
                              else 'Start the widget to generate your overlay links.')
        for name in ('Skip overlay', 'Queue overlay'):
            self.link_kinds[name].configure(text=('PUBLIC HTTPS' if public else 'LOCAL / THIS COMPUTER') if ready else 'AVAILABLE AFTER START',
                                            foreground=ACCENT if ready else MUTED)

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
        background = '#3a242e' if error else ACCENT_DARK
        self.notice_frame.configure(background=background)
        self.notice.configure(text=text, background=background, foreground=ERROR if error else ACCENT)
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

    def _resize_root(self, event):
        if event.widget is self.root:
            if event.height < 730:
                self.sidebar_plan.pack_forget()
            else:
                self.sidebar_plan.pack(fill='x', before=self.sidebar_rule)

    def _shortcut(self, action):
        if not self.locked:
            action()
        return 'break'

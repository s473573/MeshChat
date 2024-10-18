import curses


class ChatWidget:

    def __init__(self, win, pad=None, lock=None):
        # TODO: move this hardcoded stuff to config or something..
        self.BACKGROUND_CPAIR = 11
        curses.init_pair(self.BACKGROUND_CPAIR, curses.COLOR_WHITE, curses.COLOR_BLUE)

        self.win = win
        self.winy, self.winx = self.win.getbegyx()
        self.win_height, self.win_width = self.win.getmaxyx()

        self.msg_voffset, self.msg_hoffset = int(self.win_height * 0.05), int(self.win_width * 0.05)
        self.msg_minh = 1
        self.msg_minw = int(self.win_width * 0.08)
        self.msg_maxw = int(self.win_width * 0.45)

        self.msg_pad = pad
        if self.msg_pad is None:
            self.msg_pad = curses.newpad(self.win_height, self.win_width)
        # vertical offset from which to draw pad
        self.pad_offset = 0

    def _render_msg(self, text, remote=False):
        m_mxw, m_mnw = self.msg_maxw, self.msg_minw
        txtlen = len(text)

        msg_len = max(m_mnw, min(txtlen, m_mxw))+2
        hoffset = self.win_width-self.msg_hoffset-msg_len if remote else self.msg_hoffset

        mw_h = txtlen//m_mxw+1+text.count('\n')+2
        self.pad_offset += mw_h+1 if self.win_height <= mw_h+self.msg_voffset-self.pad_offset else 0

        if self.msg_pad.getmaxyx()[0] <= mw_h+self.msg_voffset:
            pad_h, pad_w = self.msg_pad.getmaxyx()
            self.msg_pad.resize(pad_h+pad_h//2, pad_w)

        msg_win = self.msg_pad.subwin(mw_h, msg_len, self.msg_voffset, hoffset)
        mw_w = msg_win.getmaxyx()[1]
        msg_win.border()

        msg_canvas = msg_win.subwin(mw_h-2, mw_w-2, 1, 1)
        msg_canvas.bkgd(' ', curses.color_pair(self.BACKGROUND_CPAIR))

        """
        https://docs.python.org/3/library/curses.html#curses.window.addstr
        """
        try:
            msg_canvas.addstr(text)
        except curses.error:
            pass

        self.msg_pad.refresh(self.pad_offset, 0, self.winy, self.winx, self.win_height, self.win_width)

        self.msg_voffset += mw_h

    def render_omsg(self, text: str):
        self._render_msg(text)

    def render_rmsg(self, text: str):
        self._render_msg(text=text, remote=True)

    def scroll_board(self, dir: int, render_height: int = -1):
        render_height = self.win_height if render_height == -1 else render_height
        if 0 <= (self.pad_offset+dir) < self.msg_pad.getmaxyx()[0]:
            self.pad_offset += dir
            self.msg_pad.refresh(self.pad_offset, 0, self.winy, self.winx, render_height, self.win_width)
